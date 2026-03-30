from sqlalchemy import Column, String, Integer, Float, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base



class AchatOffre(Base):
    __tablename__ = "achat_Offres"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    Offre_id = Column(Integer, ForeignKey("Offre.id"))

    date_debut = Column(Date)
    date_fin = Column(Date)

    actif = Column(Boolean, default=False)

    user = relationship("User", backref="achatOffres")
    Offre = relationship("Offre")