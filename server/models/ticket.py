from config.database import Base
from sqlalchemy import (
    Column, Integer, Float, String, DateTime,
    Boolean, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum


class TypeTicket(str, enum.Enum):
    TEMPS = "temps"
    DATA = "data"
    WIFI = "wifi"
    POSTE = "poste"
    ILLIMITE = "illimite"
    CREDIT = "credit"


class AccesTicket(str, enum.Enum):
    """Où ce ticket permet de se connecter : poste fixe, WiFi, ou les deux."""
    POSTE = "poste"
    WIFI = "wifi"
    LES_DEUX = "les_deux"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    type_ticket = Column(SqlEnum(TypeTicket), nullable=False)

    # Dates
    date_achat = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=True)

    # Propriétaire (optionnel) : client auquel le ticket a été vendu/rattaché —
    # permet de lister « mes tickets » et de choisir lequel utiliser à la connexion
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", foreign_keys=[user_id])

    # Lien vers une offre (optionnel)
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=True)
    offre = relationship("Offre", backref="tickets")

    # Statut
    est_actif = Column(Boolean, default=True)
    est_consomme = Column(Boolean, default=False)

    # Portée d'accès (poste fixe / wifi / les deux)
    acces = Column(SqlEnum(AccesTicket), default=AccesTicket.LES_DEUX)

    # Bon de recharge : montant crédité sur le solde du compte à l'utilisation
    credit_euros = Column(Float, nullable=True)

    # Consommation
    restant_minutes = Column(Integer, nullable=True)
    restant_data_mo = Column(Float, nullable=True)
