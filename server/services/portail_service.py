import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from models.poste import Poste, TypePoste, PosteEtat
from models.session import Session as SessionModel
from models.ticket import Ticket, TypeTicket, AccesTicket
from models.offre import Offre, is_valide_offre
from models.paiement import Paiement, TypePaiement, StatutPaiement
from models.abonnement import Abonnement
from models.user import User

from services.abonnement_service import AbonnementService
from services.historique_service import HistoriqueService
from services.paiement_service import PaiementService
from services.payment_gateway import get_gateway
from utils.code_generator import generate_code


_TYPE_OFFRE_TO_TICKET = {
    "temps": TypeTicket.TEMPS,
    "data": TypeTicket.DATA,
    "illimite": TypeTicket.ILLIMITE,
}


class PortailService:
    """Logique du portail WiFi : sessions d'accès des clients connectés en WiFi
    (rattachées à un poste virtuel « Borne WiFi », plusieurs sessions simultanées
    possibles contrairement aux postes kiosque), et achats publics en ligne
    (tickets, recharges) confirmés de façon asynchrone par la passerelle."""

    NOM_BORNE = "Borne WiFi"

    # ---------------------------------------------------------
    # BORNE VIRTUELLE
    # ---------------------------------------------------------
    @staticmethod
    def get_or_create_borne(db: Session) -> Poste:
        borne = (
            db.query(Poste)
            .filter(Poste.type_poste == TypePoste.BORNE_WIFI, Poste.nom == PortailService.NOM_BORNE)
            .first()
        )
        if borne:
            return borne

        borne = Poste(
            nom=PortailService.NOM_BORNE,
            description="Poste virtuel : accès WiFi des clients via le portail",
            type_poste=TypePoste.BORNE_WIFI,
            etat=PosteEtat.LIBRE,
            est_verrouille=False,
            est_en_ligne=True,
        )
        db.add(borne)
        db.commit()
        db.refresh(borne)
        return borne

    # ---------------------------------------------------------
    # SESSIONS WIFI
    # ---------------------------------------------------------
    @staticmethod
    def session_active_user(db: Session, user_id: int) -> SessionModel | None:
        borne = PortailService.get_or_create_borne(db)
        return (
            db.query(SessionModel)
            .filter(
                SessionModel.poste_id == borne.id,
                SessionModel.user_id == user_id,
                SessionModel.est_active == True,
            )
            .first()
        )

    @staticmethod
    def session_active_ticket(db: Session, ticket_id: int) -> SessionModel | None:
        borne = PortailService.get_or_create_borne(db)
        return (
            db.query(SessionModel)
            .filter(
                SessionModel.poste_id == borne.id,
                SessionModel.ticket_id == ticket_id,
                SessionModel.est_active == True,
            )
            .first()
        )

    @staticmethod
    def tickets_actifs_user(db: Session, user_id: int, contexte: str = "wifi") -> list[Ticket]:
        """Tickets de connexion utilisables rattachés au compte (hors bons de
        recharge), filtrés selon le contexte de connexion : `contexte="wifi"`
        exclut les tickets réservés au poste fixe, `contexte="poste"` exclut
        ceux réservés au WiFi."""
        exclu = AccesTicket.POSTE if contexte == "wifi" else AccesTicket.WIFI
        tickets = (
            db.query(Ticket)
            .filter(
                Ticket.user_id == user_id,
                Ticket.est_actif == True,
                Ticket.est_consomme == False,
                Ticket.type_ticket != TypeTicket.CREDIT,
                Ticket.acces != exclu,
            )
            .all()
        )
        return [
            t for t in tickets
            if (t.date_expiration is None or t.date_expiration.date() >= date.today())
            and (t.restant_minutes is None or t.restant_minutes > 0)
        ]

    @staticmethod
    def demarrer_user(db: Session, user_id: int, ticket_id: int | None = None) -> SessionModel:
        if PortailService.session_active_user(db, user_id):
            raise ValueError("Une session WiFi est déjà active sur ce compte")

        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        # connexion sur un ticket du compte (choisi explicitement par le client)
        if ticket_id is not None:
            ticket = db.query(Ticket).get(ticket_id)
            if not ticket or ticket.user_id != user_id:
                raise ValueError("Ce ticket n'appartient pas à votre compte")
            PortailService.valider_ticket(db, ticket.code)
            session = PortailService._creer_session(
                db, user_id=user_id, ticket_id=ticket.id,
                limite_minutes=ticket.restant_minutes, limite_data_mo=ticket.restant_data_mo,
            )
            return session

        abo = db.query(Abonnement).get(user.current_abonnement_id) if user.current_abonnement_id else None
        abo_expire = bool(abo and abo.date_fin and abo.date_fin < datetime.utcnow())
        abo_utilisable = bool(abo and abo.est_actif and not abo.est_suspendu and not abo_expire)

        if not abo_utilisable:
            tickets = PortailService.tickets_actifs_user(db, user_id)
            if tickets:
                raise ValueError("Choisissez un de vos tickets pour vous connecter")
            if abo_expire:
                raise ValueError("Votre abonnement est expiré — achetez un nouveau forfait")
            raise ValueError("Aucun abonnement actif — achetez un forfait ou utilisez un code ticket")

        limite_minutes = None if abo.illimite else abo.minutes_restantes_aujourdhui
        limite_data = None if abo.illimite else abo.data_restante_mo
        if not abo.illimite and (limite_minutes is not None and limite_minutes <= 0):
            raise ValueError("Plus de temps disponible aujourd'hui sur votre abonnement")

        return PortailService._creer_session(
            db, user_id=user_id, abonnement_id=abo.id,
            limite_minutes=limite_minutes, limite_data_mo=limite_data,
        )

    @staticmethod
    def valider_ticket(db: Session, code: str) -> Ticket:
        ticket = db.query(Ticket).filter(Ticket.code == code.strip().upper()).first()
        if not ticket:
            raise ValueError("Code ticket inconnu")
        if ticket.type_ticket == TypeTicket.CREDIT:
            raise ValueError("Ce code est un bon de recharge — utilisez-le pour créditer un compte, pas pour vous connecter")
        if ticket.acces == AccesTicket.POSTE:
            raise ValueError("Ce ticket est réservé aux postes fixes")
        if not ticket.est_actif:
            raise ValueError("Ce ticket n'est pas actif (paiement en attente ou désactivé)")
        if ticket.est_consomme:
            raise ValueError("Ce ticket est déjà entièrement consommé")
        if ticket.date_expiration and ticket.date_expiration.date() < date.today():
            raise ValueError("Ce ticket est expiré")
        if ticket.restant_minutes is not None and ticket.restant_minutes <= 0:
            raise ValueError("Ce ticket n'a plus de temps disponible")
        return ticket

    @staticmethod
    def demarrer_ticket(db: Session, code: str) -> SessionModel:
        ticket = PortailService.valider_ticket(db, code)

        session = PortailService.session_active_ticket(db, ticket.id)
        if session:
            return session  # reconnexion au même ticket : on reprend la session en cours

        return PortailService._creer_session(
            db, ticket_id=ticket.id,
            limite_minutes=ticket.restant_minutes, limite_data_mo=ticket.restant_data_mo,
        )

    @staticmethod
    def _creer_session(
        db: Session,
        user_id: int | None = None,
        ticket_id: int | None = None,
        abonnement_id: int | None = None,
        limite_minutes: int | None = None,
        limite_data_mo: float | None = None,
    ) -> SessionModel:
        borne = PortailService.get_or_create_borne(db)
        session = SessionModel(
            poste_id=borne.id,
            user_id=user_id,
            ticket_id=ticket_id,
            abonnement_id=abonnement_id,
            date_debut=datetime.utcnow(),
            est_active=True,
            est_terminee=False,
            limite_minutes=limite_minutes,
            limite_data_mo=limite_data_mo,
            consommation_minutes=0,
            consommation_data_mo=0,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        HistoriqueService.log(
            db=db,
            type_evenement="session_start",
            description="Session WiFi démarrée via le portail",
            user_id=user_id,
            ticket_id=ticket_id,
            poste_id=borne.id,
        )
        return session

    @staticmethod
    def actualiser(db: Session, session: SessionModel) -> SessionModel:
        """Consommation « paresseuse » : pas de heartbeat côté WiFi, le temps écoulé
        est comptabilisé (et débité du ticket/abonnement) à chaque consultation.
        Ferme la session si la limite est atteinte."""
        if not session.est_active:
            return session

        ecoulees = int((datetime.utcnow() - session.date_debut).total_seconds() // 60)
        delta = ecoulees - (session.consommation_minutes or 0)
        if delta > 0:
            session.consommation_minutes = ecoulees

            if session.ticket_id and session.ticket and session.ticket.restant_minutes is not None:
                session.ticket.restant_minutes = max(0, session.ticket.restant_minutes - delta)
                if session.ticket.restant_minutes == 0:
                    session.ticket.est_consomme = True
            elif session.abonnement_id:
                AbonnementService.consommer(db, session.abonnement_id, minutes=delta)

            db.commit()

        if session.limite_minutes is not None and session.consommation_minutes >= session.limite_minutes:
            # une session restée ouverte (onglet fermé sans déconnexion) ne peut pas
            # avoir consommé plus que sa limite : on borne la valeur enregistrée
            session.consommation_minutes = session.limite_minutes
            db.commit()
            PortailService.terminer(db, session)

        return session

    @staticmethod
    def terminer(db: Session, session: SessionModel) -> SessionModel:
        from services.session_service import SessionService

        if session.est_active:
            SessionService.fermer_session(db, session.id)

        # fermer_session reverrouille le poste (sécurité kiosque) — non pertinent
        # pour la borne virtuelle, qui doit rester disponible.
        borne = PortailService.get_or_create_borne(db)
        borne.est_verrouille = False
        borne.etat = PosteEtat.LIBRE
        borne.est_en_ligne = True
        db.commit()
        return session

    @staticmethod
    def serialiser_session(session: SessionModel) -> dict:
        restant = None
        if session.limite_minutes is not None:
            restant = max(0, session.limite_minutes - (session.consommation_minutes or 0))
        return {
            "id": session.id,
            "est_active": session.est_active,
            "date_debut": session.date_debut,
            "date_fin": session.date_fin,
            "consommation_minutes": session.consommation_minutes,
            "consommation_data_mo": session.consommation_data_mo,
            "limite_minutes": session.limite_minutes,
            "limite_data_mo": session.limite_data_mo,
            "restant_minutes": restant,
            "illimite": session.limite_minutes is None,
            "ticket_code": session.ticket.code if session.ticket else None,
        }

    # ---------------------------------------------------------
    # PANIER (client connecté) — articles et forfaits en une commande, réglée
    # avec le solde du compte (rechargeable en ligne). Validation globale
    # (stock + solde) avant exécution pour éviter les paniers à moitié débités.
    # ---------------------------------------------------------
    @staticmethod
    def commander_panier(
        db: Session,
        user_id: int,
        items: list[dict],
        utiliser_solde: bool = True,
        type_paiement=None,
        operateur_id: int | None = None,
        statut_commande_articles: str | None = None,
    ) -> dict:
        """Commande groupée d'articles et de forfaits. Deux modes :
        - portail (utiliser_solde=True) : réglée sur le solde du compte ;
        - caisse (utiliser_solde=False + type_paiement) : encaissée au comptoir
          par un opérateur (espèces, carte, mobile money...)."""
        from models.article import Article
        from services.article_service import ArticleService
        from services.abonnement_service import AbonnementService as AboService

        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")
        if not items:
            raise ValueError("Panier vide")
        if not utiliser_solde and type_paiement is None:
            raise ValueError("Moyen de paiement requis pour un encaissement en caisse")

        # --- Validation globale ---
        total = 0.0
        lignes: list[tuple[str, object, int]] = []
        for item in items:
            type_item = item.get("type")
            quantite = int(item.get("quantite", 1))
            if quantite < 1:
                raise ValueError("Quantité invalide")

            if type_item == "article":
                article = db.query(Article).get(item.get("id"))
                if not article or not article.actif:
                    raise ValueError(f"Article {item.get('id')} indisponible")
                if article.stock is not None and article.stock < quantite:
                    raise ValueError(f"Stock insuffisant pour « {article.nom} » ({article.stock} restant)")
                total += article.prix * quantite
                lignes.append(("article", article, quantite))

            elif type_item == "forfait":
                offre = db.query(Offre).get(item.get("id"))
                if not offre:
                    raise ValueError(f"Forfait {item.get('id')} introuvable")
                valide = is_valide_offre(offre)
                if not valide["valide"]:
                    raise ValueError(f"« {offre.nom} » : {valide['detail']}")
                total += offre.prix * quantite
                lignes.append(("forfait", offre, quantite))

            else:
                raise ValueError(f"Type d'élément inconnu : {type_item}")

        if utiliser_solde and user.solde_euros < total:
            raise ValueError(
                f"Solde insuffisant : {user.solde_euros:.2f}€ disponible pour un panier de "
                f"{total:.2f}€ — rechargez votre compte"
            )

        # --- Exécution (chaque ligne réutilise les services existants : stock,
        # mouvements, paiements et abonnements restent tracés à l'identique) ---
        details_lignes = []
        for type_item, objet, quantite in lignes:
            for _ in range(quantite):
                if type_item == "article":
                    ArticleService.acheter_article(
                        db=db, article_id=objet.id, user_id=user_id,
                        utiliser_solde=utiliser_solde, type_paiement=type_paiement,
                        operateur_id=operateur_id, statut_commande=statut_commande_articles,
                    )
                else:
                    AboService.souscrire(
                        db=db, user_id=user_id, offre_id=objet.id,
                        utiliser_solde=utiliser_solde, type_paiement=type_paiement,
                        operateur_id=operateur_id,
                    )
            details_lignes.append({"type": type_item, "nom": objet.nom, "quantite": quantite, "prix_unitaire": objet.prix})

        db.refresh(user)
        HistoriqueService.log(
            db=db,
            type_evenement="achat",
            description=f"Commande panier portail : {len(lignes)} ligne(s), {total:.2f}€",
            user_id=user_id,
            details={"lignes": details_lignes, "total": total},
        )

        return {"total": total, "lignes": details_lignes, "nouveau_solde": user.solde_euros}

    # ---------------------------------------------------------
    # ACHATS PUBLICS EN LIGNE (sans compte)
    # ---------------------------------------------------------
    @staticmethod
    def commander_ticket(db: Session, offre_id: int, gateway_nom: str) -> dict:
        """Achat de ticket en ligne : le ticket est pré-généré INACTIF et lié au
        paiement — la confirmation de la passerelle (webhook ou confirmer-demo)
        l'active, et l'acheteur récupère son code via statut_commande."""
        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")
        valide = is_valide_offre(offre)
        if not valide["valide"]:
            raise ValueError(valide["detail"])

        while True:
            code = generate_code()
            if not db.query(Ticket).filter(Ticket.code == code).first():
                break

        ticket = Ticket(
            code=code,
            type_ticket=_TYPE_OFFRE_TO_TICKET.get(
                offre.type_offre.value if hasattr(offre.type_offre, "value") else offre.type_offre,
                TypeTicket.TEMPS,
            ),
            offre_id=offre.id,
            date_expiration=offre.date_expiration,
            restant_minutes=getattr(offre, "duree_minutes", None),
            restant_data_mo=getattr(offre, "quota_mo", None),
            est_actif=False,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        secret = uuid.uuid4().hex
        paiement = Paiement(
            ticket_id=ticket.id,
            montant=offre.prix,
            devise="EUR",
            type_paiement=TypePaiement.PAYPAL,
            statut=StatutPaiement.EN_ATTENTE,
            details={"intent": "achat_ticket", "gateway": gateway_nom, "secret": secret},
        )
        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        gateway = get_gateway(gateway_nom)
        commande = gateway.creer_commande(
            montant=offre.prix,
            devise="EUR",
            reference=f"paiement-{paiement.id}",
            description=f"Ticket {offre.nom} (achat en ligne)",
        )
        paiement.reference = commande.order_id
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement_en_ligne_cree",
            description=f"Commande de ticket en ligne ({offre.nom}, {offre.prix}€) via {gateway_nom}",
            ticket_id=ticket.id,
            details={"paiement_id": paiement.id},
        )

        return {
            "paiement_id": paiement.id,
            "approval_url": commande.approval_url,
            "secret": secret,
            "montant": offre.prix,
        }

    @staticmethod
    def commander_recharge(db: Session, user_id: int, montant: float, gateway_nom: str) -> dict:
        """Recharge de solde en ligne (depuis le portail, connecté ou non) —
        réutilise l'intent recharge_solde existant, avec un secret par commande
        pour permettre le suivi public du statut."""
        result = PaiementService.creer_commande_en_ligne(
            db=db, gateway_nom=gateway_nom, intent="recharge_solde",
            user_id=user_id, montant=montant,
        )
        secret = uuid.uuid4().hex
        paiement = db.query(Paiement).get(result["paiement_id"])
        paiement.details = {**(paiement.details or {}), "secret": secret}
        db.commit()

        return {
            "paiement_id": result["paiement_id"],
            "approval_url": result["approval_url"],
            "secret": secret,
            "montant": montant,
        }

    @staticmethod
    def commander_offre(db: Session, user_id: int, offre_id: int, gateway_nom: str) -> dict:
        """Achat de forfait en ligne pour un compte (intent achat_offre existant)."""
        result = PaiementService.creer_commande_en_ligne(
            db=db, gateway_nom=gateway_nom, intent="achat_offre",
            user_id=user_id, offre_id=offre_id,
        )
        secret = uuid.uuid4().hex
        paiement = db.query(Paiement).get(result["paiement_id"])
        paiement.details = {**(paiement.details or {}), "secret": secret}
        db.commit()

        return {
            "paiement_id": result["paiement_id"],
            "approval_url": result["approval_url"],
            "secret": secret,
        }

    @staticmethod
    def statut_commande(db: Session, paiement_id: int, secret: str) -> dict:
        """Suivi public d'une commande en ligne, protégé par le secret retourné à la
        création (empêche l'énumération des paiements)."""
        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Commande introuvable")

        details = paiement.details or {}
        if not secret or details.get("secret") != secret:
            raise ValueError("Secret de commande invalide")

        data = {
            "paiement_id": paiement.id,
            "statut": paiement.statut.value if hasattr(paiement.statut, "value") else paiement.statut,
            "montant": paiement.montant,
        }
        if paiement.statut == StatutPaiement.SUCCES and details.get("intent") == "achat_ticket" and paiement.ticket:
            data["ticket_code"] = paiement.ticket.code
        return data
