from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean,
    ForeignKey, Enum as SqlEnum, JSON, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class TypePaiement(str, enum.Enum):
    ESPECES = "especes"
    CARTE = "carte"
    MOBILE_MONEY = "mobile_money"
    VIREMENT = "virement"
    CODE_PREPAYE = "code_prepaye"
    GRATUIT = "gratuit"


class StatutPaiement(str, enum.Enum):
    SUCCES = "succes"
    ECHEC = "echec"
    ANNULE = "annule"
    EN_ATTENTE = "en_attente"


class Paiement(Base):
    __tablename__ = "paiements"

    id = Column(Integer, primary_key=True, index=True)

    # --- Relations principales ---
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", foreign_keys=[user_id])

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User", foreign_keys=[operateur_id])

    achat_id = Column(Integer, ForeignKey("achats.id"), nullable=True)
    achat = relationship("Achat", backref="paiement")

    # --- Informations financières ---
    montant = Column(Float, nullable=False)
    devise = Column(String, default="EUR")

    type_paiement = Column(SqlEnum(TypePaiement), nullable=False)
    statut = Column(SqlEnum(StatutPaiement), default=StatutPaiement.SUCCES)

    reference = Column(String, nullable=True)
    details = Column(JSON, nullable=True)

    # --- Dates ---
    date_paiement = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL) OR (ticket_id IS NOT NULL)",
            name="check_paiement_identite"
        ),
    )
