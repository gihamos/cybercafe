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


class LimiteSessionsAtteinteError(ValueError):
    """Levée quand le nombre max de sessions actives simultanées (ticket, offre ou
    compte — voir verifier_limite_sessions) est atteint lors d'une nouvelle
    connexion. Porte les infos de la session active la plus ancienne de la portée
    concernée, que l'appelant (routeur portail ou ws_poste) traduit en réponse
    structurée pour que le client propose de la déconnecter afin de continuer."""

    def __init__(self, portee: str, limite: int, session: SessionModel):
        self.portee = portee  # "ticket" | "compte"
        self.limite = limite
        self.session = session
        super().__init__(
            f"Nombre maximum de connexions simultanées atteint ({portee} : {limite}) "
            "— déconnectez une session active pour continuer"
        )


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

    # ---------------------------------------------------------
    # LIMITE DE SESSIONS ACTIVES SIMULTANÉES (ticket / offre / compte)
    # ---------------------------------------------------------
    @staticmethod
    def sessions_actives(
        db: Session, ticket_id: int | None = None, user_id: int | None = None,
        abonnement_id: int | None = None,
    ) -> list[SessionModel]:
        """Sessions actives pour un ticket, un compte ou un abonnement, TOUS canaux
        confondus (poste kiosque et WiFi) — contrairement à session_active_user/
        session_active_ticket ci-dessus, qui ne regardent que la borne WiFi. Triées
        de la plus ancienne à la plus récente."""
        query = db.query(SessionModel).filter(SessionModel.est_active == True)
        if ticket_id is not None:
            query = query.filter(SessionModel.ticket_id == ticket_id)
        elif user_id is not None:
            query = query.filter(SessionModel.user_id == user_id)
        elif abonnement_id is not None:
            query = query.filter(SessionModel.abonnement_id == abonnement_id)
        else:
            return []
        return query.order_by(SessionModel.date_debut.asc()).all()

    @staticmethod
    def _verifier_portee(
        db: Session, portee: str, limite: int | None,
        sessions_scope_kwargs: dict, deconnecter_session_id: int | None,
    ) -> None:
        # NULL = 1 (comportement historique : une seule session à la fois) — voir
        # User.max_sessions_simultanees pour le raisonnement ; ne jamais basculer en
        # illimité par défaut sur un système d'accès payant.
        limite = limite if limite is not None else 1
        actives = PortailService.sessions_actives(db, **sessions_scope_kwargs)
        if len(actives) < limite:
            return

        if deconnecter_session_id is not None:
            cible = next((s for s in actives if s.id == deconnecter_session_id), None)
            if cible:
                from services.session_service import SessionService
                SessionService.fermer_session(db, cible.id)
                return

        raise LimiteSessionsAtteinteError(portee, limite, actives[0])

    @staticmethod
    def verifier_limite_sessions(
        db: Session,
        ticket: Ticket | None = None,
        abonnement: Abonnement | None = None,
        user: User | None = None,
        deconnecter_session_id: int | None = None,
    ) -> None:
        """À appeler juste avant de créer une nouvelle session : vérifie le plafond de
        connexions simultanées de chaque portée concernée (ticket, forfait/abonnement,
        compte), indépendamment — la première limite atteinte bloque. Si une limite
        est atteinte et que `deconnecter_session_id` désigne bien une des sessions
        actives de cette portée, elle est déconnectée pour libérer une place ; sinon
        LimiteSessionsAtteinteError est levée avec la session active la plus ancienne
        de cette portée, à proposer à la déconnexion."""
        if ticket is not None:
            limite = ticket.max_sessions_simultanees
            if limite is None and ticket.offre:
                limite = ticket.offre.max_sessions_simultanees
            PortailService._verifier_portee(
                db, "ticket", limite, {"ticket_id": ticket.id}, deconnecter_session_id
            )

        if abonnement is not None and abonnement.offre:
            PortailService._verifier_portee(
                db, "forfait", abonnement.offre.max_sessions_simultanees,
                {"abonnement_id": abonnement.id}, deconnecter_session_id
            )

        if user is not None:
            PortailService._verifier_portee(
                db, "compte", user.max_sessions_simultanees,
                {"user_id": user.id}, deconnecter_session_id
            )

    @staticmethod
    def demarrer_user(
        db: Session,
        user_id: int,
        ticket_id: int | None = None,
        ip_client: str | None = None,
        utiliser_abonnement: bool = False,
        deconnecter_session_id: int | None = None,
    ) -> SessionModel:
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        # connexion sur un ticket du compte (choisi explicitement par le client)
        if ticket_id is not None:
            ticket = db.query(Ticket).get(ticket_id)
            if not ticket or ticket.user_id != user_id:
                raise ValueError("Ce ticket n'appartient pas à votre compte")
            PortailService.valider_ticket(db, ticket.code)
            PortailService.verifier_limite_sessions(
                db, ticket=ticket, user=user, deconnecter_session_id=deconnecter_session_id
            )
            session = PortailService._creer_session(
                db, user_id=user_id, ticket_id=ticket.id,
                limite_minutes=ticket.restant_minutes, limite_data_mo=ticket.restant_data_mo,
                ip_client=ip_client,
            )
            return session

        abo = db.query(Abonnement).get(user.current_abonnement_id) if user.current_abonnement_id else None
        abo_expire = bool(abo and abo.date_fin and abo.date_fin < datetime.utcnow())
        abo_utilisable = bool(abo and abo.est_actif and not abo.est_suspendu and not abo_expire)
        tickets = PortailService.tickets_actifs_user(db, user_id)

        # Le client a le droit de choisir quel forfait actif utiliser pour se
        # connecter : si l'abonnement ET au moins un ticket sont utilisables, on
        # ne tranche jamais silencieusement — le client doit choisir explicitement
        # (ticket_id ci-dessus, ou utiliser_abonnement=True ici) via le sélecteur.
        if not utiliser_abonnement:
            if abo_utilisable and tickets:
                raise ValueError("Plusieurs forfaits actifs — choisissez celui à utiliser pour vous connecter")
            if not abo_utilisable:
                if tickets:
                    raise ValueError("Choisissez un de vos tickets pour vous connecter")
                if abo_expire:
                    raise ValueError("Votre abonnement est expiré — achetez un nouveau forfait")
                raise ValueError("Aucun abonnement actif — achetez un forfait ou utilisez un code ticket")
        elif not abo_utilisable:
            raise ValueError("Votre abonnement n'est plus utilisable")

        limite_minutes = None if abo.illimite else abo.minutes_restantes_aujourdhui
        limite_data = None if abo.illimite else abo.data_restante_mo
        if not abo.illimite and (limite_minutes is not None and limite_minutes <= 0):
            raise ValueError("Plus de temps disponible aujourd'hui sur votre abonnement")

        PortailService.verifier_limite_sessions(
            db, abonnement=abo, user=user, deconnecter_session_id=deconnecter_session_id
        )

        return PortailService._creer_session(
            db, user_id=user_id, abonnement_id=abo.id,
            limite_minutes=limite_minutes, limite_data_mo=limite_data,
            ip_client=ip_client,
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
    def demarrer_ticket(
        db: Session, code: str, ip_client: str | None = None, deconnecter_session_id: int | None = None,
    ) -> SessionModel:
        ticket = PortailService.valider_ticket(db, code)

        # Remarque : pas de raccourci « une seule session active = c'est forcément le
        # même appareil qui se reconnecte » — un ticket anonyme n'a aucun identifiant
        # de device pour le distinguer d'une vraie 2e connexion simultanée. Tout passe
        # par verifier_limite_sessions, qui gère aussi bien le cas normal (limite=1,
        # aucune session active) que le cas multi-session configuré.
        PortailService.verifier_limite_sessions(
            db, ticket=ticket, user=ticket.user, deconnecter_session_id=deconnecter_session_id
        )

        return PortailService._creer_session(
            db, ticket_id=ticket.id,
            limite_minutes=ticket.restant_minutes, limite_data_mo=ticket.restant_data_mo,
            ip_client=ip_client,
        )

    @staticmethod
    def _creer_session(
        db: Session,
        user_id: int | None = None,
        ticket_id: int | None = None,
        abonnement_id: int | None = None,
        limite_minutes: int | None = None,
        limite_data_mo: float | None = None,
        ip_client: str | None = None,
    ) -> SessionModel:
        from services.reseau_service import ReseauService

        borne = PortailService.get_or_create_borne(db)
        mac_client = ReseauService.resoudre_mac_depuis_ip(ip_client) if ip_client else None

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
            ip_client=ip_client,
            mac_client=mac_client,
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

        ReseauService.autoriser(db, session)

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

        # --- Exécution (chaque ligne réutilise les services existants : stock et
        # mouvements restent tracés à l'identique) ---
        # Un forfait acheté ici devient un TICKET rattaché au compte (comme en
        # caisse — voir VenteCaisseService), jamais une activation directe
        # d'abonnement : le client choisit ensuite lequel utiliser pour se
        # connecter (plusieurs tickets peuvent coexister, voir /portail/mes-tickets).
        details_lignes = []
        for type_item, objet, quantite in lignes:
            tickets_generes = []
            for _ in range(quantite):
                if type_item == "article":
                    ArticleService.acheter_article(
                        db=db, article_id=objet.id, user_id=user_id,
                        utiliser_solde=utiliser_solde, type_paiement=type_paiement,
                        operateur_id=operateur_id, statut_commande=statut_commande_articles,
                    )
                else:
                    ticket = PortailService._acheter_forfait_comme_ticket(
                        db=db, user_id=user_id, offre=objet,
                        utiliser_solde=utiliser_solde, type_paiement=type_paiement,
                        operateur_id=operateur_id,
                    )
                    tickets_generes.append(ticket.code)
            ligne = {"type": type_item, "nom": objet.nom, "quantite": quantite, "prix_unitaire": objet.prix}
            if tickets_generes:
                ligne["tickets_codes"] = tickets_generes
            details_lignes.append(ligne)

        db.refresh(user)
        HistoriqueService.log(
            db=db,
            type_evenement="achat",
            description=f"Commande panier portail : {len(lignes)} ligne(s), {total:.2f}€",
            user_id=user_id,
            details={"lignes": details_lignes, "total": total},
        )

        return {"total": total, "lignes": details_lignes, "nouveau_solde": user.solde_euros}

    @staticmethod
    def _acheter_forfait_comme_ticket(
        db: Session,
        user_id: int,
        offre: Offre,
        utiliser_solde: bool,
        type_paiement,
        operateur_id: int | None,
    ) -> Ticket:
        """Règle un forfait (solde ou caisse) et matérialise l'achat par un ticket de
        connexion actif rattaché au compte — jamais par une activation directe
        d'abonnement, pour que le client puisse choisir/cumuler plusieurs forfaits
        (voir tickets_actifs_user / /portail/mes-tickets)."""
        if utiliser_solde:
            paiement = PaiementService.payer_via_solde(db, user_id, offre.prix)
        else:
            paiement = PaiementService.creer_paiement(
                db=db, montant=offre.prix, type_paiement=type_paiement,
                user_id=user_id, operateur_id=operateur_id,
            )

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
            user_id=user_id,
            date_expiration=offre.date_expiration,
            restant_minutes=getattr(offre, "duree_minutes", None),
            restant_data_mo=getattr(offre, "quota_mo", None),
            est_actif=True,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        if paiement is not None:
            paiement.ticket_id = ticket.id
            db.commit()

        return ticket

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

    @staticmethod
    def lister_paiements_enrichis(
        db: Session, user_id: int | None = None, ticket_id: int | None = None, limit: int = 50
    ) -> list[dict]:
        """Historique unifié « tickets & factures » : chaque paiement, quelle que soit
        son origine (portail, caisse, poste), avec la nature du produit réglé
        (forfait/ticket, article, ou simple recharge de solde) pour affichage direct
        dans un onglet reçus — au lieu de forcer le client à deviner ce qu'il a payé
        à partir du seul montant. Filtré par user_id (compte) ou ticket_id (session
        anonyme sur un poste, rattachée à un ticket sans compte)."""
        from models.achat_article import AchatArticle

        query = db.query(Paiement)
        if user_id is not None:
            query = query.filter(Paiement.user_id == user_id)
        elif ticket_id is not None:
            query = query.filter(Paiement.ticket_id == ticket_id)
        else:
            return []

        paiements = query.order_by(Paiement.date_paiement.desc()).limit(limit).all()

        resultats = []
        for p in paiements:
            # Reconnu comme recharge uniquement via le marqueur posé à la commande
            # (voir commander_recharge) — sinon libellé neutre plutôt qu'une
            # supposition erronée (ex: paiement solde d'une session Pay & Connect).
            if (p.details or {}).get("intent") == "recharge_solde":
                nature, libelle = "credit", "Recharge de solde"
            else:
                nature, libelle = "credit", "Paiement"

            if p.ticket_id and p.ticket:
                if p.ticket.type_ticket == TypeTicket.CREDIT:
                    nature, libelle = "credit", f"Bon de recharge {p.ticket.code}"
                else:
                    nature = "forfait"
                    libelle = f"{p.ticket.offre.nom} ({p.ticket.code})" if p.ticket.offre else f"Ticket {p.ticket.code}"
            else:
                article = db.query(AchatArticle).filter(AchatArticle.paiement_id == p.id).first()
                if article:
                    nature = "article"
                    libelle = article.article.nom if article.article else "Article"

            resultats.append({
                "id": p.id,
                "montant": p.montant,
                "devise": p.devise,
                "type_paiement": p.type_paiement,
                "statut": p.statut,
                "date_paiement": p.date_paiement,
                "nature": nature,
                "libelle": libelle,
            })
        return resultats
