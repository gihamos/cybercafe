from sqlalchemy import (
    Column, Integer, Float, DateTime, Boolean,
    ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import datetime


class Achat(Base):
    __tablename__ = "achats"

    id = Column(Integer, primary_key=True, index=True)

    # --- Relations principales ---
    # Client qui bénéficie de l'achat
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="achats")

    # Opérateur qui a réalisé la vente
    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operateur = relationship("User", foreign_keys=[operateur_id])

    # Produit acheté : Offre OU Ticket
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    abonnement_id = Column(Integer, ForeignKey("abonnements.id"))


    offre = relationship("Offre")
    ticket = relationship("Ticket")

    # --- Informations financières ---
    prix_paye = Column(Float, nullable=False)

    # --- Dates ---
    date_achat = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=True)

    # --- Statut ---
    est_actif = Column(Boolean, default=True)
    est_consomme = Column(Boolean, default=False)

    # --- Consommation ---
    minutes_restantes = Column(Integer, nullable=True)
    data_restante_mo = Column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(offre_id IS NOT NULL) OR (ticket_id IS NOT NULL)",
            name="check_achat_produit"
        ),
    )

def is_valid_achat(achat: Achat) -> dict[str, any]:
    """Vérifie si un achat est encore valide."""

    if not achat.est_actif:
        return {
            "valide": False,
            "detail": "Cet achat n'est plus actif."
        }

    if achat.est_consomme:
        return {
            "valide": False,
            "detail": "Ce produit a déjà été consommé."
        }

    if achat.date_expiration and achat.date_expiration < datetime.utcnow():
        return {
            "valide": False,
            "detail": f"Le produit a expiré le {achat.date_expiration.date()}."
        }

    return {
        "valide": True,
        "detail": "L'achat est valide."
    }
