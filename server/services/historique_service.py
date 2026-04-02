from sqlalchemy.orm import Session
from datetime import datetime
from models.historique import Historique


class HistoriqueService:

    # ---------------------------------------------------------
    # ENREGISTRER UN ÉVÉNEMENT
    # ---------------------------------------------------------
    @staticmethod
    def log(
        db: Session,
        type_evenement: str,
        description: str,
        user_id: int | None = None,
        poste_id: int | None = None,
        ticket_id: int | None = None,
        details: dict | None = None
    ):
        entry = Historique(
            type_evenement=type_evenement,
            description=description,
            user_id=user_id,
            poste_id=poste_id,
            ticket_id=ticket_id,
            details=details,
            date_evenement=datetime.utcnow()
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        return entry

    # ---------------------------------------------------------
    # RÉCUPÉRER L’HISTORIQUE GLOBAL
    # ---------------------------------------------------------
    @staticmethod
    def get_all(db: Session, limit: int = 100, offset: int = 0):
        return (
            db.query(Historique)
            .order_by(Historique.date_evenement.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    # ---------------------------------------------------------
    # RÉCUPÉRER L’HISTORIQUE D’UN UTILISATEUR
    # ---------------------------------------------------------
    @staticmethod
    def get_by_user(db: Session, user_id: int, limit: int = 100):
        return (
            db.query(Historique)
            .filter(Historique.user_id == user_id)
            .order_by(Historique.date_evenement.desc())
            .limit(limit)
            .all()
        )

    # ---------------------------------------------------------
    # RÉCUPÉRER L’HISTORIQUE D’UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def get_by_poste(db: Session, poste_id: int, limit: int = 100):
        return (
            db.query(Historique)
            .filter(Historique.poste_id == poste_id)
            .order_by(Historique.date_evenement.desc())
            .limit(limit)
            .all()
        )

    # ---------------------------------------------------------
    # RÉCUPÉRER L’HISTORIQUE D’UN TICKET
    # ---------------------------------------------------------
    @staticmethod
    def get_by_ticket(db: Session, ticket_id: int, limit: int = 100):
        return (
            db.query(Historique)
            .filter(Historique.ticket_id == ticket_id)
            .order_by(Historique.date_evenement.desc())
            .limit(limit)
            .all()
        )

    # ---------------------------------------------------------
    # SUPPRIMER L’HISTORIQUE (purge)
    # ---------------------------------------------------------
    @staticmethod
    def purge(db: Session, days: int = 30):
        """Supprime les logs plus vieux que X jours."""
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(days=days)

        deleted = (
            db.query(Historique)
            .filter(Historique.date_evenement < threshold)
            .delete()
        )

        db.commit()
        return deleted
