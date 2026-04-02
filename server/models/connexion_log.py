from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class ConnexionLog(Base):
    __tablename__ = "connexion_logs"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)

    date_debut = Column(DateTime, default=datetime.utcnow)
    date_fin = Column(DateTime, nullable=True)

    consommation_minutes = Column(Integer, default=0)
    consommation_data_mo = Column(Float, default=0)

    session = relationship("Session", back_populates="connexions")
    poste = relationship("Poste", back_populates="connexions")
