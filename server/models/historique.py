from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Enum as SqlEnum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class TypeEvenement(str, enum.Enum):
    CONNEXION = "connexion"
    DECONNEXION = "deconnexion"
    CHANGEMENT_POSTE = "changement_poste"
    ACHAT = "achat"
    CONSOMMATION = "consommation"
    ABONNEMENT_ACTIVATION = "abonnement_activation"
    ABONNEMENT_EXPIRATION = "abonnement_expiration"
    IMPRESSION = "impression"
    POSTE_BLOQUE = "poste_bloque"
    POSTE_DEBLOQUE = "poste_debloque"
    ERREUR_SYSTEME = "erreur_systeme"
    ACTION_OPERATEUR = "action_operateur",
    NOTIFICATION_USER = "notification_user"
    AUTRE = "autre"


class Historique(Base):
    __tablename__ = "historiques"

    id = Column(Integer, primary_key=True, index=True)

    # Type d'événement
    type_evenement = Column(SqlEnum(TypeEvenement), nullable=False)

    # Description lisible
    description = Column(String, nullable=False)

    # Données supplémentaires (flexible)
    details = Column(JSON, nullable=True)

    # Qui a fait l'action ?
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    operateur = relationship("User", foreign_keys=[operateur_id])
    
    ticket_id=Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket=relationship("Ticket", foreign_keys=[ticket_id])

    # Où ?
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)
    poste = relationship("Poste")

    # Quand ?
    timestamp = Column(DateTime, default=datetime.utcnow)
