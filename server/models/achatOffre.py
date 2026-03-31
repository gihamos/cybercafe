from sqlalchemy import Column, String, Integer, Float, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base
from models.offre import Offre


class AchatOffre(Base):
    __tablename__ = "achat_offres"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    offre_id = Column(Integer, ForeignKey("offre.id"))

    date_debut = Column(Date)
    date_fin = Column(Date)

    actif = Column(Boolean, default=False)

    user = relationship(
        "User",
        back_populates="achat_offres",
        foreign_keys=[user_id]   # 🔥 IMPORTANT
    )

    offre = relationship("Offre", backref="achat_offres")