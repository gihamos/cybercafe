from sqlalchemy import Column, String, Integer, Float, Date, Boolean, ForeignKey,DateTime
from sqlalchemy.orm import relationship
from config.database import Base
from models.offre import Offre
from datetime import date,datetime


class Abonnement(Base):
    __tablename__ = "abonnements"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    offre_id = Column(Integer, ForeignKey("offre.id"))

    date_debut = Column(Date)
    date_fin = Column(Date)

    is_actif = Column(Boolean, default=False)
    
    restant_minutes = Column(Integer, nullable=True)
    restant_data_mo = Column(Float, nullable=True)
    date_achat=Column(DateTime,default=datetime.today())
    date_expire=Column(DateTime,nullable=True)

    user = relationship(
        "User",
        back_populates="abonnements",
        foreign_keys=[user_id]   # 
    )

    offre = relationship("Offre", backref="abonnements")
    
    
def is_valide_abonnement(abonnement: Abonnement)->dict[str,any]:
    """_summary_

    Args:
        abonnement (Abonnement): _description_

    Returns:
        dict[str,any]: retourne deux champs valide si l'abonnement est valide et message pour le message
    """
    if(not abonnement.is_actif):
        return {
            "valide":False,
            "detail":"l'abonnement n'est pas activé"
        }
    elif abonnement.restant_minutes and abonnement.restant_minutes<6:
        return {
            "valide":False,
            "detail":"l'abonnement n'a plus de temps"
}
    elif abonnement.restant_data_mo and abonnement.restant_data_mo<10:
        return {
        "valide":False,
        "detail":"l'abonnement n'a plus de data"
        }
    elif abonnement.date_expire and abonnement.date_expire<datetime.today():
        return {
    "valide":False,
    "detail":"l'abonnement n'est expiré"
        }
    
    else:
        return {
    "valide":True,
    "detail":"l'abonnement est valide"
}
