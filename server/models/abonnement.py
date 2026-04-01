from sqlalchemy import Column, String, Integer, Float, Date, Boolean, ForeignKey,DateTime
from sqlalchemy.orm import relationship
from config.database import Base
from models.offre import Offre
from datetime import date,datetime

class Abonnement(Base):
    __tablename__ = "abonnements"

    id = Column(Integer, primary_key=True, index=True)

    # Relations
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="abonnement")

    achat_id = Column(Integer, ForeignKey("achats.id"), nullable=False)
    achat = relationship("Achat", back_populates="abonnement")

    # L'offre qui définit les règles de l'abonnement
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=False)
    offre = relationship("Offre")

    # Dates
    date_debut = Column(DateTime, default=datetime.utcnow)
    date_fin = Column(DateTime, nullable=True)

    # Statut
    est_actif = Column(Boolean, default=True)
    est_suspendu = Column(Boolean, default=False)

    # Consommation
    minutes_par_jour = Column(Integer, nullable=True)
    minutes_restantes_aujourdhui = Column(Integer, nullable=True)

    data_totale_mo = Column(Float, nullable=True)
    data_restante_mo = Column(Float, nullable=True)

    illimite = Column(Boolean, default=False)

def is_valide_abonnement(abonnement: Abonnement)->dict[str,any]:
    """_summary_

    Args:
        abonnement (Abonnement): _description_

    Returns:
        dict[str,any]: retourne deux champs valide si l'abonnement est valide et message pour le message
    """
    if(not abonnement.est_actif):
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
