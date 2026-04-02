from sqlalchemy import (
    Column, Integer, Float, String, Enum as SqlEnum,
    ForeignKey, Boolean,DateTime
)
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import datetime
import enum


class TypeProfilBP(str, enum.Enum):
    OFFRE = "offre"
    ABONNEMENT = "abonnement"
    TICKET = "ticket"
    USER = "user"
    POSTE = "poste"


class BandePassanteProfil(Base):
    __tablename__ = "bande_passante_profils"

    id = Column(Integer, primary_key=True, index=True)

    # Type de profil (offre, ticket, user, etc.)
    type_profil = Column(SqlEnum(TypeProfilBP), nullable=False)

    # Relations optionnelles
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=True)
    abonnement_id = Column(Integer, ForeignKey("abonnements.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)

    # Limites de vitesse (en Mbps)
    download_mbps = Column(Float, nullable=True)
    upload_mbps = Column(Float, nullable=True)

    # Quotas (en Mo)
    quota_journalier_mo = Column(Float, nullable=True)
    quota_mensuel_mo = Column(Float, nullable=True)

    # Blocage automatique quand quota atteint
    bloquer_si_depasse = Column(Boolean, default=False)


class BandePassanteUsage(Base):
    __tablename__ = "bande_passante_usage"

    id = Column(Integer, primary_key=True, index=True)

    # Lié à une session
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    session = relationship("Session")

    # Lié à un ticket (WiFi)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")

    # Lié à un utilisateur
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")

    # Consommation
    data_download_mo = Column(Float, default=0)
    data_upload_mo = Column(Float, default=0)
    data_total_mo = Column(Float, default=0)

    # Date
    date_enregistrement = Column(DateTime, default=datetime.utcnow)