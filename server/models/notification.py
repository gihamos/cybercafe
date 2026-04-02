from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    ForeignKey, Enum as SqlEnum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class TypeNotification(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"
    SESSION = "session"
    IMPRESSION = "impression"
    PAIEMENT = "paiement"
    ABONNEMENT = "abonnement"
    POSTE = "poste"
    BANDE_PASSANTE = "bande_passante"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # Destinataires possibles
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User",foreign_keys=[user_id])

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)
    poste = relationship("Poste")

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User", foreign_keys=[operateur_id])

    # Contenu
    titre = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type_notification = Column(SqlEnum(TypeNotification), nullable=False)

    # Statut
    est_lue = Column(Boolean, default=False)
    est_envoyee = Column(Boolean, default=False)
    est_expiree = Column(Boolean, default=False)

    # Dates
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_envoi = Column(DateTime, nullable=True)
    date_lecture = Column(DateTime, nullable=True)
    date_expiration = Column(DateTime, nullable=True)

    # Données supplémentaires
    details = Column(JSON, nullable=True)
