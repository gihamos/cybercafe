from sqlalchemy.orm import Session
from datetime import datetime

from models.user import User, UserRole, is_validUser
from models.paiement import Paiement, TypePaiement
from models.notification import Notification, TypeNotification  #
from models.historique import TypeEvenement

from services.historique_service import HistoriqueService

from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.user import User
from models.poste import Poste
from models.ticket import Ticket



class NotificationService:

    # ---------------------------------------------------------
    # ENVOYER À UN UTILISATEUR
    # ---------------------------------------------------------
    @staticmethod
    def send_to_user(
        db: Session,
        user_id: int,
        titre: str,
        message: str,
        type_notification: TypeNotification,
        details: dict | None = None,
        expire_in_minutes: int | None = None
    ):
        notif = Notification(
            user_id=user_id,
            titre=titre,
            message=message,
            type_notification=type_notification,
            details=details,
            est_envoyee=True,
            date_envoi=datetime.utcnow(),
            date_expiration=(
                datetime.utcnow() + timedelta(minutes=expire_in_minutes)
                if expire_in_minutes else None
            )
        )

        db.add(notif)
        db.commit()
        db.refresh(notif)

        HistoriqueService.log(
            db=db,
            type_evenement=TypeEvenement.NOTIFICATION_USER,
            description=f"Notification envoyée à l'utilisateur {user_id}",
            user_id=user_id,
            details={"titre": titre}
        )

        return notif

    # ---------------------------------------------------------
    # ENVOYER À UN TICKET (WiFi)
    # ---------------------------------------------------------
    @staticmethod
    def send_to_ticket(
        db: Session,
        ticket_id: int,
        titre: str,
        message: str,
        type_notification: TypeNotification,
        details: dict | None = None
    ):
        notif = Notification(
            ticket_id=ticket_id,
            titre=titre,
            message=message,
            type_notification=type_notification,
            est_envoyee=True,
            date_envoi=datetime.utcnow(),
            details=details
        )

        db.add(notif)
        db.commit()
        db.refresh(notif)

        HistoriqueService.log(
            db=db,
            type_evenement="notification_ticket",
            description=f"Notification envoyée au ticket {ticket_id}",
            details={"titre": titre}
        )

        return notif

    # ---------------------------------------------------------
    # ENVOYER À UN POSTE (client PC)
    # ---------------------------------------------------------
    @staticmethod
    def send_to_poste(
        db: Session,
        poste_id: int,
        titre: str,
        message: str,
        type_notification: TypeNotification,
        details: dict | None = None
    ):
        notif = Notification(
            poste_id=poste_id,
            titre=titre,
            message=message,
            type_notification=type_notification,
            est_envoyee=True,
            date_envoi=datetime.utcnow(),
            details=details
        )

        db.add(notif)
        db.commit()
        db.refresh(notif)

        HistoriqueService.log(
            db=db,
            type_evenement="notification_poste",
            description=f"Notification envoyée au poste {poste_id}",
            details={"titre": titre}
        )

        return notif

    # ---------------------------------------------------------
    # ENVOYER À UN OPÉRATEUR
    # ---------------------------------------------------------
    @staticmethod
    def send_to_operateur(
        db: Session,
        operateur_id: int,
        titre: str,
        message: str,
        type_notification: TypeNotification,
        details: dict | None = None
    ):
        notif = Notification(
            operateur_id=operateur_id,
            titre=titre,
            message=message,
            type_notification=type_notification,
            est_envoyee=True,
            date_envoi=datetime.utcnow(),
            details=details
        )

        db.add(notif)
        db.commit()
        db.refresh(notif)

        HistoriqueService.log(
            db=db,
            type_evenement="notification_operateur",
            description=f"Notification envoyée à l'opérateur {operateur_id}",
            user_id=operateur_id,
            details={"titre": titre}
        )

        return notif

    # ---------------------------------------------------------
    # NOTIFICATION SYSTÈME (sans destinataire)
    # ---------------------------------------------------------
    @staticmethod
    def send_system(
        db: Session,
        titre: str,
        message: str,
        details: dict | None = None
    ):
        notif = Notification(
            titre=titre,
            message=message,
            type_notification=TypeNotification.SYSTEM,
            est_envoyee=True,
            date_envoi=datetime.utcnow(),
            details=details
        )

        db.add(notif)
        db.commit()
        db.refresh(notif)

        HistoriqueService.log(
            db=db,
            type_evenement="notification_system",
            description=f"Notification système : {titre}",
            details=details
        )

        return notif

    # ---------------------------------------------------------
    # MARQUER COMME LUE
    # ---------------------------------------------------------
    @staticmethod
    def mark_as_read(db: Session, notif_id: int):
        notif = db.query(Notification).get(notif_id)
        if not notif:
            raise ValueError("Notification introuvable")

        notif.est_lue = True
        notif.date_lecture = datetime.utcnow()
        db.commit()

        return notif

    # ---------------------------------------------------------
    # RÉCUPÉRER LES NOTIFICATIONS D’UN USER
    # ---------------------------------------------------------
    @staticmethod
    def get_user_notifications(db: Session, user_id: int, only_unread=False):
        query = db.query(Notification).filter(Notification.user_id == user_id)

        if only_unread:
            query = query.filter(Notification.est_lue == False)

        return query.order_by(Notification.date_creation.desc()).all()

    # ---------------------------------------------------------
    # EXPIRER LES NOTIFICATIONS
    # ---------------------------------------------------------
    @staticmethod
    def expire_old_notifications(db: Session):
        now = datetime.utcnow()
        expired = (
            db.query(Notification)
            .filter(Notification.date_expiration != None)
            .filter(Notification.date_expiration < now)
            .all()
        )

        for notif in expired:
            notif.est_expiree = True

        db.commit()

        return len(expired)
