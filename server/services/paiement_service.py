from sqlalchemy.orm import Session
from datetime import datetime

from models.paiement import Paiement, TypePaiement
from models.user import User
from models.ticket import Ticket

from server.services.historique_service import HistoriqueService
from server.services.notification_service import NotificationService
from models.notification import TypeNotification


class PaiementService:

    # ---------------------------------------------------------
    # CRÉER UN PAIEMENT (générique)
    # ---------------------------------------------------------
    @staticmethod
    def creer_paiement(
        db: Session,
        montant: float,
        type_paiement: TypePaiement,
        user_id: int | None = None,
        ticket_id: int | None = None,
        statut: str = "succes"
    ):
        if montant <= 0:
            raise ValueError("Montant invalide")

        paiement = Paiement(
            montant=montant,
            type_paiement=type_paiement,
            user_id=user_id,
            ticket_id=ticket_id,
            statut=statut,
            date_paiement=datetime.utcnow()
        )

        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        HistoriqueService.log(
            db=db,
            type_evenement="paiement",
            description=f"Paiement de {montant}€ ({type_paiement})",
            user_id=user_id,
            ticket_id=ticket_id,
            details={"statut": statut}
        )

        return paiement

    # ---------------------------------------------------------
    # PAIEMENT POUR UN USER (solde NON utilisé)
    # ---------------------------------------------------------
    @staticmethod
    def payer_user(
        db: Session,
        user_id: int,
        montant: float,
        type_paiement: TypePaiement
    ):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        paiement = PaiementService.creer_paiement(
            db=db,
            montant=montant,
            type_paiement=type_paiement,
            user_id=user_id
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            titre="Paiement effectué",
            message=f"Un paiement de {montant}€ a été enregistré.",
            type_notification=TypeNotification.PAIEMENT
        )

        return paiement

    # ---------------------------------------------------------
    # PAIEMENT POUR UN TICKET (toujours direct)
    # ---------------------------------------------------------
    @staticmethod
    def payer_ticket(
        db: Session,
        ticket_id: int,
        montant: float,
        type_paiement: TypePaiement
    ):
        ticket = db.query(Ticket).get(ticket_id)
        if not ticket:
            raise ValueError("Ticket introuvable")

        paiement = PaiementService.creer_paiement(
            db=db,
            montant=montant,
            type_paiement=type_paiement,
            ticket_id=ticket_id
        )

        return paiement

    # ---------------------------------------------------------
    # PAIEMENT VIA SOLDE UTILISATEUR
    # ---------------------------------------------------------
    @staticmethod
    def payer_via_solde(db: Session, user_id: int, montant: float):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if user.solde_euros < montant:
            raise ValueError("Solde insuffisant")

        user.solde_euros -= montant
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement_solde",
            description=f"Paiement via solde de {montant}€",
            user_id=user_id,
            details={"nouveau_solde": user.solde_euros}
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            titre="Paiement via solde",
            message=f"Un montant de {montant}€ a été débité de votre solde.",
            type_notification=TypeNotification.PAIEMENT
        )

        return user.solde_euros

    # ---------------------------------------------------------
    # REMBOURSEMENT
    # ---------------------------------------------------------
    @staticmethod
    def rembourser(db: Session, paiement_id: int):
        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Paiement introuvable")

        if paiement.statut == "annule":
            raise ValueError("Paiement déjà annulé")

        paiement.statut = "annule"
        db.commit()

        # Si paiement lié à un user → remboursement dans le solde
        if paiement.user_id:
            user = db.query(User).get(paiement.user_id)
            user.solde_euros += paiement.montant
            db.commit()

            NotificationService.send_to_user(
                db=db,
                user_id=user.id,
                titre="Remboursement effectué",
                message=f"Un remboursement de {paiement.montant}€ a été crédité sur votre solde.",
                type_notification=TypeNotification.PAIEMENT
            )

        HistoriqueService.log(
            db=db,
            type_evenement="remboursement",
            description=f"Remboursement du paiement {paiement_id}",
            user_id=paiement.user_id,
            ticket_id=paiement.ticket_id
        )

        return paiement
