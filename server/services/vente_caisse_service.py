import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from models.article import Article
from models.offre import Offre, is_valide_offre
from models.paiement import Paiement, TypePaiement, StatutPaiement
from models.ticket import Ticket, TypeTicket
from models.user import User, UserRole
from models.achat_article import AchatArticle, StatutCommande
from models.mouvement_stock import MouvementStock, TypeMouvementStock
from models.vente_caisse import VenteCaisse, LigneVenteCaisse, StatutVenteCaisse, TypeLigneVente

from services.historique_service import HistoriqueService
from services.in_person_gateway import get_in_person_gateway
from utils.code_generator import generate_code
from utils.security import hash_password


USERNAME_CLIENT_PASSAGE = "client_de_passage"


class VenteCaisseService:
    """Caisse professionnelle : encaissement groupé (ticket de caisse référencé,
    scannable) et remboursement total ou partiel avec remise en stock.

    Un client de caisse est un simple acheteur : les ventes anonymes sont portées
    par le compte système « client de passage » (jamais connectable), ce qui garde
    la comptabilité des paiements intacte sans exiger de compte wifi/poste."""

    # ---------------------------------------------------------
    # CLIENT DE PASSAGE (compte système)
    # ---------------------------------------------------------
    @staticmethod
    def get_or_create_client_passage(db: Session) -> User:
        user = db.query(User).filter(User.username == USERNAME_CLIENT_PASSAGE).first()
        if user:
            return user
        user = User(
            username=USERNAME_CLIENT_PASSAGE,
            email="client.de.passage@systeme.local",
            first_name="Client",
            last_name="de passage",
            password=hash_password(secrets.token_hex(24)),  # jamais connectable
            role=UserRole.client,
            is_active=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ---------------------------------------------------------
    # ENCAISSEMENT D'UN PANIER (ticket de caisse)
    # ---------------------------------------------------------
    @staticmethod
    def _generer_reference(db: Session) -> str:
        while True:
            ref = f"TC{datetime.utcnow().strftime('%y%m%d')}{generate_code(6)}"
            if not db.query(VenteCaisse).filter(VenteCaisse.reference == ref).first():
                return ref

    @staticmethod
    def encaisser(
        db: Session,
        operateur_id: int,
        items: list[dict],
        type_paiement: TypePaiement,
        user_id: int | None = None,
    ) -> VenteCaisse:
        """items : [{"type": "article"|"forfait"|"bon", "id"?: int, "montant"?: float,
        "quantite": int}] — pour un bon, `montant` remplace `id`.
        Forfait vendu à un client identifié → abonnement ; à un client de passage →
        ticket de connexion (code imprimé sur le ticket de caisse)."""
        if not items:
            raise ValueError("Panier vide")

        user = db.query(User).get(user_id) if user_id else None
        if user_id and not user:
            raise ValueError("Client introuvable")

        # --- validation globale + total ---
        lignes_prep: list[dict] = []
        total = 0.0
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
                lignes_prep.append({"type": TypeLigneVente.ARTICLE, "article": article,
                                    "designation": article.nom, "prix": article.prix, "quantite": quantite})

            elif type_item == "forfait":
                offre = db.query(Offre).get(item.get("id"))
                if not offre:
                    raise ValueError(f"Forfait {item.get('id')} introuvable")
                valide = is_valide_offre(offre)
                if not valide["valide"]:
                    raise ValueError(f"« {offre.nom} » : {valide['detail']}")
                total += offre.prix * quantite
                lignes_prep.append({"type": TypeLigneVente.FORFAIT, "offre": offre,
                                    "designation": f"Forfait {offre.nom}", "prix": offre.prix, "quantite": quantite})

            elif type_item == "bon":
                montant = float(item.get("montant") or 0)
                if montant <= 0:
                    raise ValueError("Montant de bon invalide")
                total += montant * quantite
                lignes_prep.append({"type": TypeLigneVente.BON, "montant": montant,
                                    "designation": f"Bon de recharge {montant:.2f}€", "prix": montant, "quantite": quantite})

            else:
                raise ValueError(f"Type de produit inconnu : {type_item}")

        # --- validation du paiement (carte / mobile money via le fournisseur) ---
        valeur_type = type_paiement.value if hasattr(type_paiement, "value") else type_paiement
        reference_paiement = None
        gateway = get_in_person_gateway(valeur_type)
        if gateway:
            reference_client = f"caisse-{operateur_id}-{int(datetime.utcnow().timestamp())}"
            try:
                resultat = gateway.valider_paiement(total, "EUR", reference_client, {})
            except Exception as e:
                raise ValueError(f"Fournisseur {valeur_type} injoignable : {e}")
            if not resultat.succes:
                raise ValueError(f"Paiement {valeur_type} refusé par le fournisseur (statut : {resultat.statut})")
            reference_paiement = resultat.reference

        porteur = user or VenteCaisseService.get_or_create_client_passage(db)

        # --- un seul paiement pour tout le ticket de caisse ---
        paiement = Paiement(
            user_id=porteur.id,
            montant=total,
            type_paiement=type_paiement,
            operateur_id=operateur_id,
            statut=StatutPaiement.SUCCES,
            reference=reference_paiement,
            date_paiement=datetime.utcnow(),
        )
        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        vente = VenteCaisse(
            reference=VenteCaisseService._generer_reference(db),
            operateur_id=operateur_id,
            user_id=user.id if user else None,
            paiement_id=paiement.id,
            type_paiement=valeur_type,
            total=total,
        )
        db.add(vente)
        db.flush()

        # --- exécution des lignes ---
        for prep in lignes_prep:
            ligne = LigneVenteCaisse(
                vente_id=vente.id,
                type_ligne=prep["type"],
                designation=prep["designation"],
                prix_unitaire=prep["prix"],
                quantite=prep["quantite"],
            )

            if prep["type"] == TypeLigneVente.ARTICLE:
                article = prep["article"]
                ligne.article_id = article.id
                for _ in range(prep["quantite"]):
                    db.add(AchatArticle(
                        article_id=article.id, user_id=vente.user_id,
                        paiement_id=paiement.id, operateur_id=operateur_id,
                        prix=article.prix, statut_commande=StatutCommande.RECUPEREE.value,
                    ))
                if article.stock is not None:
                    article.stock -= prep["quantite"]
                    db.add(MouvementStock(
                        article_id=article.id, type_mouvement=TypeMouvementStock.VENTE,
                        variation=-prep["quantite"], stock_apres=article.stock,
                        motif=f"Vente caisse {vente.reference}", operateur_id=operateur_id,
                    ))

            elif prep["type"] == TypeLigneVente.FORFAIT:
                offre = prep["offre"]
                ligne.offre_id = offre.id
                # un forfait vendu en caisse devient un ticket de connexion : rattaché
                # au compte du client identifié (il choisira quand l'utiliser), ou
                # simplement imprimé sur le ticket pour un client de passage
                ticket = VenteCaisseService._generer_ticket_connexion(db, offre)
                if user:
                    ticket.user_id = user.id
                ligne.ticket_id = ticket.id

            elif prep["type"] == TypeLigneVente.BON:
                ticket = Ticket(
                    code=VenteCaisseService._code_ticket_libre(db),
                    type_ticket=TypeTicket.CREDIT,
                    credit_euros=prep["montant"],
                    user_id=user.id if user else None,
                )
                db.add(ticket)
                db.flush()
                ligne.ticket_id = ticket.id

            db.add(ligne)

        db.commit()
        db.refresh(vente)

        HistoriqueService.log(
            db=db,
            type_evenement="paiement",
            description=f"Ticket de caisse {vente.reference} : {len(lignes_prep)} ligne(s), {total:.2f}€ ({valeur_type})",
            user_id=vente.user_id,
            operateur_id=operateur_id,
            details={"vente_id": vente.id, "reference": vente.reference},
        )
        return vente

    @staticmethod
    def _code_ticket_libre(db: Session) -> str:
        while True:
            code = generate_code()
            if not db.query(Ticket).filter(Ticket.code == code).first():
                return code

    @staticmethod
    def _generer_ticket_connexion(db: Session, offre: Offre) -> Ticket:
        from router.tickets import _TYPE_OFFRE_TO_TICKET  # mapping type offre → ticket
        ticket = Ticket(
            code=VenteCaisseService._code_ticket_libre(db),
            type_ticket=_TYPE_OFFRE_TO_TICKET.get(offre.type_offre, TypeTicket.TEMPS),
            offre_id=offre.id,
            date_expiration=offre.date_expiration,
            restant_minutes=getattr(offre, "duree_minutes", None),
            restant_data_mo=getattr(offre, "quota_mo", None),
        )
        db.add(ticket)
        db.flush()
        return ticket

    # ---------------------------------------------------------
    # RECHERCHE / CONSULTATION
    # ---------------------------------------------------------
    @staticmethod
    def get_par_reference(db: Session, reference: str) -> VenteCaisse:
        vente = db.query(VenteCaisse).filter(VenteCaisse.reference == reference.strip().upper()).first()
        if not vente:
            raise ValueError("Ticket de caisse introuvable")
        return vente

    # ---------------------------------------------------------
    # REMBOURSEMENT (total ou partiel, par ligne)
    # ---------------------------------------------------------
    @staticmethod
    def rembourser(
        db: Session,
        reference: str,
        lignes_demandees: list[dict],
        operateur_id: int,
        rembourser_sur_solde: bool = False,
    ) -> dict:
        """lignes_demandees : [{"ligne_id": int, "quantite": int}].
        Règles : produits frais jamais remboursés ; articles remis en stock ;
        bons/tickets non consommés désactivés ; abonnements liés désactivés."""
        vente = VenteCaisseService.get_par_reference(db, reference)
        if vente.statut == StatutVenteCaisse.REMBOURSEE:
            raise ValueError("Ce ticket de caisse a déjà été entièrement remboursé")

        # politique de remboursement : validité du ticket de caisse (Paramètres)
        from services.config_service import ConfigService
        validite_jours = ConfigService.get_config(db).get("caisse.validite_ticket_jours") or 30
        age_jours = (datetime.utcnow() - vente.date_vente).days
        if age_jours > int(validite_jours):
            raise ValueError(
                f"Ticket de caisse expiré ({age_jours} jours) : la politique de remboursement "
                f"est de {int(validite_jours)} jours"
            )
        if not lignes_demandees:
            raise ValueError("Aucune ligne à rembourser")

        lignes_par_id = {ligne.id: ligne for ligne in vente.lignes}

        # --- validation ---
        operations: list[tuple[LigneVenteCaisse, int]] = []
        montant = 0.0
        for demande in lignes_demandees:
            ligne = lignes_par_id.get(demande.get("ligne_id"))
            if not ligne:
                raise ValueError(f"Ligne {demande.get('ligne_id')} absente de ce ticket")
            quantite = int(demande.get("quantite", 1))
            restant = ligne.quantite - ligne.quantite_remboursee
            if quantite < 1 or quantite > restant:
                raise ValueError(f"Quantité invalide pour « {ligne.designation} » ({restant} remboursable)")

            if ligne.type_ligne == TypeLigneVente.ARTICLE and ligne.article:
                if ligne.article.type_conservation == "frais":
                    raise ValueError(f"« {ligne.article.nom} » est un produit frais : non remboursable")
            if ligne.type_ligne in (TypeLigneVente.BON, TypeLigneVente.FORFAIT) and ligne.ticket:
                if ligne.ticket.est_consomme:
                    raise ValueError(f"« {ligne.designation} » a déjà été utilisé : non remboursable")

            operations.append((ligne, quantite))
            montant += ligne.prix_unitaire * quantite

        # --- exécution ---
        for ligne, quantite in operations:
            ligne.quantite_remboursee += quantite

            if ligne.type_ligne == TypeLigneVente.ARTICLE and ligne.article:
                if ligne.article.stock is not None:
                    ligne.article.stock += quantite
                    db.add(MouvementStock(
                        article_id=ligne.article.id, type_mouvement=TypeMouvementStock.AJUSTEMENT,
                        variation=quantite, stock_apres=ligne.article.stock,
                        motif=f"Remboursement {vente.reference}", operateur_id=operateur_id,
                    ))

            elif ligne.ticket:
                ligne.ticket.est_actif = False

            elif ligne.type_ligne == TypeLigneVente.FORFAIT and ligne.abonnement_id:
                from models.abonnement import Abonnement
                abonnement = db.query(Abonnement).get(ligne.abonnement_id)
                if abonnement:
                    abonnement.est_actif = False

        vente.montant_rembourse = (vente.montant_rembourse or 0) + montant
        restant_total = sum(l.quantite - l.quantite_remboursee for l in vente.lignes)
        vente.statut = StatutVenteCaisse.REMBOURSEE if restant_total == 0 else StatutVenteCaisse.PARTIELLEMENT_REMBOURSEE

        if vente.paiement and vente.statut == StatutVenteCaisse.REMBOURSEE:
            vente.paiement.statut = StatutPaiement.ANNULE

        # re-crédit sur le solde du client identifié (sinon rendu en espèces, tracé)
        if rembourser_sur_solde:
            if not vente.user_id:
                raise ValueError("Remboursement sur solde impossible : vente sans compte client")
            client = db.query(User).get(vente.user_id)
            client.solde_euros += montant

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="remboursement",
            description=f"Remboursement {montant:.2f}€ sur ticket {vente.reference}"
                        f" ({'solde' if rembourser_sur_solde else 'espèces'})",
            user_id=vente.user_id,
            operateur_id=operateur_id,
            details={"vente_id": vente.id, "montant": montant},
        )

        return {"reference": vente.reference, "montant_rembourse": montant,
                "statut": vente.statut.value, "sur_solde": rembourser_sur_solde}
