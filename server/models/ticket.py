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


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    type_ticket = Column(SqlEnum(TypeTicket), nullable=False)

    # Dates
    date_achat = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=True)

    # Lien vers une offre (optionnel)
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=True)
    offre = relationship("Offre", back_populates="tickets")

    # Statut
    est_actif = Column(Boolean, default=True)
    est_consomme = Column(Boolean, default=False)

    # Consommation
    restant_minutes = Column(Integer, nullable=True)
    restant_data_mo = Column(Float, nullable=True)
