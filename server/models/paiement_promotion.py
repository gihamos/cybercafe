from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class PaiementPromotion(Base):
    """Trace chaque promotion effectivement appliquée à un paiement, avec le montant
    qu'elle a fait économiser — un paiement peut en cumuler plusieurs (promotions
    automatiques + un code), voir services/promotion_service.py::appliquer. Permet
    d'afficher après coup, sur le reçu et dans l'interface Paiements, quelles
    promotions ont joué et de combien chacune a réduit le prix."""

    __tablename__ = "paiement_promotions"

    id = Column(Integer, primary_key=True, index=True)

    paiement_id = Column(Integer, ForeignKey("paiements.id"), nullable=False)
    paiement = relationship("Paiement", backref="promotions_appliquees")

    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=False)
    promotion = relationship("Promotion")

    montant_reduction = Column(Float, nullable=False)
    date_application = Column(DateTime, default=datetime.utcnow)
