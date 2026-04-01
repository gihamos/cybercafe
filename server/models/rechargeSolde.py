from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class RechargeSolde(Base):
    __tablename__ = "recharges_soldes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    paiement_id = Column(Integer, ForeignKey("paiements.id"), nullable=False)
    paiement = relationship("Paiement")

    montant = Column(Float, nullable=False)

    date_recharge = Column(DateTime, default=datetime.utcnow)
