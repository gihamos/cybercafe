from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    poste_id=Column(Integer, ForeignKey("postes.id"), nullable=True)

    date_debut = Column(DateTime, default=datetime.utcnow)
    date_fin = Column(DateTime, nullable=True)

    consommation_minutes = Column(Integer, default=0)
    consommation_data = Column(Float, default=0)

    user = relationship("User", backref="sessions")
    ticket = relationship("Ticket", backref="sessions")
    poste = relationship("Poste", backref="sessions")