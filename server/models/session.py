from sqlalchemy import (
    Column, Integer, Float, DateTime, Boolean,
    ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
from server.models.connexion_log import ConnexionLog


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)

    # --- Relations ---
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    abonnement_id = Column(Integer, ForeignKey("abonnements.id"), nullable=True)
    achat_id = Column(Integer, ForeignKey("achats.id"), nullable=True)

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)

    user = relationship("User", backref="sessions")
    ticket = relationship("Ticket", backref="sessions")
    abonnement = relationship("Abonnement", backref="sessions")
    achat = relationship("Achat", backref="sessions")
    poste = relationship("Poste", backref="sessions")

    # --- Dates ---
    date_debut = Column(DateTime, default=datetime.utcnow)
    date_fin = Column(DateTime, nullable=True)

    # --- Statut ---
    est_active = Column(Boolean, default=True)
    est_terminee = Column(Boolean, default=False)

    # --- Consommation ---
    consommation_minutes = Column(Integer, default=0)
    consommation_data_mo = Column(Float, default=0)

    # --- Limites (selon l'offre ou abonnement) ---
    limite_minutes = Column(Integer, nullable=True)
    limite_data_mo = Column(Float, nullable=True)
    
    # log
    connexions = relationship("ConnexionLog", back_populates="session")


    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL) OR (ticket_id IS NOT NULL)",
            name="check_session_identite"
        ),
    )


def is_valid_session(session: Session) -> dict[str, any]:

    if not session.est_active:
        return {"valide": False, "detail": "La session n'est plus active."}

    if session.date_fin and session.date_fin < datetime.utcnow():
        return {"valide": False, "detail": "La session est expirée."}

    if session.limite_minutes is not None:
        if session.consommation_minutes >= session.limite_minutes:
            return {"valide": False, "detail": "Temps maximum atteint."}

    if session.limite_data_mo is not None:
        if session.consommation_data_mo >= session.limite_data_mo:
            return {"valide": False, "detail": "Quota data atteint."}

    return {"valide": True, "detail": "Session valide."}
