from config.database import Base
from sqlalchemy import Column, Integer, Float,String,Date,ForeignKey
from sqlalchemy.orm import relationship
from datetime import date

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    code=Column(String,unique=True,nullable=False)
    description=Column(String,nullable=True)
    date_achat = Column(Date, default=date.today)
    date_expiration = Column(Date, nullable=True)
    offre_id = Column(Integer, ForeignKey("offre.id"))

    restant_minutes = Column(Integer, nullable=True)
    restant_data = Column(Float, nullable=True)
    offre = relationship("Offre",backref="tickets")
    
