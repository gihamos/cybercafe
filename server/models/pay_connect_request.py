from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class StatutPayConnect(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    CONFIRME = "confirme"
    REFUSE = "refuse"
    ANNULE = "annule"


class PayConnectRequest(Base):
    """Demande de connexion rapide payante ('Pay & Connect') sur un poste, sans ticket
    ni abonnement : le client choisit une durée, paie en espèces au comptoir (encaissée
    et validée par un opérateur) et la session démarre directement sur ce poste. Non
    transférable (aucun code n'est délivré) et les minutes non consommées ne sont pas
    conservées : la demande est un artefact ponctuel, pas un moyen de paiement réutilisable."""

    __tablename__ = "pay_connect_requests"

    id = Column(Integer, primary_key=True, index=True)

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)
    poste = relationship("Poste")

    minutes = Column(Integer, nullable=False)
    montant = Column(Float, nullable=False)

    statut = Column(SqlEnum(StatutPayConnect), default=StatutPayConnect.EN_ATTENTE, nullable=False)

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    date_creation = Column(DateTime, default=datetime.utcnow)
    date_traitement = Column(DateTime, nullable=True)
