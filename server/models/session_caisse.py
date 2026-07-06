from sqlalchemy import Column, Integer, Float, DateTime, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class SessionCaisse(Base):
    """Session de caisse d'un opérateur : ouverture avec un fond de départ,
    clôture avec rapprochement (théorique = fond + total espèces encaissées
    pendant la session, vs réel compté physiquement)."""

    __tablename__ = "sessions_caisse"

    id = Column(Integer, primary_key=True, index=True)

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operateur = relationship("User")

    montant_ouverture = Column(Float, nullable=False, default=0)
    date_ouverture = Column(DateTime, default=datetime.utcnow)

    montant_cloture_theorique = Column(Float, nullable=True)
    montant_cloture_reel = Column(Float, nullable=True)
    ecart = Column(Float, nullable=True)
    date_cloture = Column(DateTime, nullable=True)

    est_ouverte = Column(Boolean, default=True)
    notes = Column(String, nullable=True)
