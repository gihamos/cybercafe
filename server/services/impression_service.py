from sqlalchemy.orm import Session
from datetime import datetime

from models.impression import (
    Impression,
    StatutImpression,
    TypeImpression,
    OrigineImpression
)
from models.paiement import TypePaiement
from server.services.paiement_service import PaiementService
from server.services.notification_service import NotificationService
from server.services.historique_service import HistoriqueService
from models.notification import TypeNotification


class ImpressionService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE DEMANDE D’IMPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def creer_impression(
        db: Session,
        origine: OrigineImpression,
        fichier_nom: str,
        fichier_path: str,
        pages_liste: list[int],
        type_impression: TypeImpression,
        recto_verso: bool,
        prix_par_page: float,
        user_id: int | None = None,
        ticket_id: int | None = None,
        poste_id: int | None = None,
        achat_id: int | None = None,
        operateur_id: int | None = None,
        details: dict | None = None
    ):
        if prix_par_page <= 0:
            raise ValueError("Prix par page invalide")

        pages_total = len(pages_liste)

        impression = Impression(
            origine=origine,
            user_id=user_id,
            ticket_id=ticket_id,
            poste_id=poste_id,
            achat_id=achat_id,
            operateur_id=operateur_id,
            fichier_nom=fichier_nom,
            fichier_path=fichier_path,
            fichier_type=fichier_nom.split(".")[-1].lower(),
            pages_liste=pages_liste,
            pages_total=pages_total,
            selection_pages=",".join(map(str, pages_liste)),
            recto_verso=recto_verso,
            type_impression=type_impression,
            prix_par_page=prix_par_page,
            prix_total=pages_total * prix_par_page,
            statut=StatutImpression.EN_ATTENTE,
            details=details,
            date_impression=datetime.utcnow()
        )

        db.add(impression)
        db.commit()
        db.refresh(impression)

        HistoriqueService.log(
            db=db,
            type_evenement="impression_create",
            description=f"Demande d'impression créée ({pages_total} pages)",
            user_id=user_id,
            ticket_id=ticket_id,
            poste_id=poste_id,
            details={"prix_total": impression.prix_total}
        )

        return impression

    # ---------------------------------------------------------
    # 2. PAYER L’IMPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def payer_impression(
        db: Session,
        impression_id: int,
        utiliser_solde: bool = False,
        type_paiement: TypePaiement | None = None
    ):
        impression = db.query(Impression).get(impression_id)
        if not impression:
            raise ValueError("Impression introuvable")

        montant = impression.prix_total

        if utiliser_solde:
            if not impression.user_id:
                raise ValueError("Le paiement via solde nécessite un utilisateur")
            PaiementService.payer_via_solde(db, impression.user_id, montant)
        else:
            paiement = PaiementService.creer_paiement(
                db=db,
                montant=montant,
                type_paiement=type_paiement,
                user_id=impression.user_id,
                ticket_id=impression.ticket_id
            )
            impression.paiement_id = paiement.id

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="impression_pay",
            description=f"Paiement impression ({montant}€)",
            user_id=impression.user_id,
            ticket_id=impression.ticket_id,
            details={"impression_id": impression.id}
        )

        return impression

    # ---------------------------------------------------------
    # 3. CHANGER LE STATUT
    # ---------------------------------------------------------
    @staticmethod
    def set_statut(db: Session, impression_id: int, statut: StatutImpression, message_erreur: str | None = None):
        impression = db.query(Impression).get(impression_id)
        if not impression:
            raise ValueError("Impression introuvable")

        impression.statut = statut
        impression.message_erreur = message_erreur
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="impression_status",
            description=f"Statut impression → {statut}",
            user_id=impression.user_id,
            ticket_id=impression.ticket_id,
            poste_id=impression.poste_id,
            details={"erreur": message_erreur}
        )

        # Notification utilisateur
        if impression.user_id:
            if statut == StatutImpression.SUCCES:
                NotificationService.send_to_user(
                    db=db,
                    user_id=impression.user_id,
                    titre="Impression terminée",
                    message=f"Votre impression '{impression.fichier_nom}' est prête.",
                    type_notification=TypeNotification.IMPRESSION
                )
            elif statut == StatutImpression.ECHEC:
                NotificationService.send_to_user(
                    db=db,
                    user_id=impression.user_id,
                    titre="Erreur d'impression",
                    message=f"L'impression a échoué : {message_erreur}",
                    type_notification=TypeNotification.IMPRESSION
                )

        return impression

    # ---------------------------------------------------------
    # 4. ANNULER UNE IMPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def annuler_impression(db: Session, impression_id: int):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.ANNULEE
        )

    # ---------------------------------------------------------
    # 5. RÉCUPÉRER LES IMPRESSIONS (filtres)
    # ---------------------------------------------------------
    @staticmethod
    def rechercher_impressions(
        db: Session,
        user_id: int | None = None,
        ticket_id: int | None = None,
        poste_id: int | None = None,
        statut: StatutImpression | None = None,
        origine: OrigineImpression | None = None
    ):
        query = db.query(Impression)

        if user_id:
            query = query.filter(Impression.user_id == user_id)

        if ticket_id:
            query = query.filter(Impression.ticket_id == ticket_id)

        if poste_id:
            query = query.filter(Impression.poste_id == poste_id)

        if statut:
            query = query.filter(Impression.statut == statut)

        if origine:
            query = query.filter(Impression.origine == origine)

        return query.order_by(Impression.date_impression.desc()).all()

    # ---------------------------------------------------------
    # 6. MARQUER COMME EN COURS
    # ---------------------------------------------------------
    @staticmethod
    def demarrer_impression(db: Session, impression_id: int):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.EN_COURS
        )

    # ---------------------------------------------------------
    # 7. MARQUER COMME RÉUSSIE
    # ---------------------------------------------------------
    @staticmethod
    def terminer_impression(db: Session, impression_id: int):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.SUCCES
        )

    # ---------------------------------------------------------
    # 8. MARQUER COMME ÉCHOUÉE
    # ---------------------------------------------------------
    @staticmethod
    def erreur_impression(db: Session, impression_id: int, message: str):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.ECHEC,
            message_erreur=message
        )
