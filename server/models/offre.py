from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import datetime
import enum
from sqlalchemy import Enum as SqlEnum


class TypeOffre(str, enum.Enum):
    TEMPS = "temps"
    DATA = "data"
    ILLIMITE = "illimite"

class TypeDuree(int,enum.Enum):
    MINUTE:1
    HEURE:60
    JOUR:1440
    HEBDO:10080
    MOIS:43200
    ANNEE:518400
    
    
    

class Offre(Base):
    __tablename__ = "offre"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)

    type_offre = Column(SqlEnum(TypeOffre), nullable=False)

    debit_upload_kbps = Column(Integer, nullable=True)
    debit_download_kbps = Column(Integer, nullable=True)
    prix = Column(Float, nullable=False)

    date_creation = Column(DateTime, default=datetime.today)
    date_expiration = Column(DateTime, nullable=True)

    description = Column(String, nullable=True)
    is_actif = Column(Boolean, default=True)
    typedelai=Column(SqlEnum(TypeDuree),nullable=True)
    valeur_delai=Column(int,nullable=True)


    __mapper_args__ = {
        "polymorphic_on": type_offre,
        "polymorphic_identity": "offre"
    }


# Offre Temps
class offreTemps(Offre):
    __tablename__ = "offre_temps"

    id = Column(Integer, ForeignKey("offre.id"), primary_key=True)
    duree_minutes = Column(Integer, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": TypeOffre.TEMPS
    }


# Offre Data
class OffreData(Offre):
    __tablename__ = "offre_data"

    id = Column(Integer, ForeignKey("offre.id"), primary_key=True)
    quota_mo = Column(Float, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": TypeOffre.DATA
    }


# Offre Illimité
class OffreIllimite(Offre):
    __tablename__ = "offre_illimite"

    id = Column(Integer, ForeignKey("offre.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": TypeOffre.ILLIMITE
    }
    
    
def is_valide_offre(offre: Offre)->dict[str,any]:
    """_summary_


    Args:
        offre (Offre): _description_


    Returns:
        dict[str,any]: retourne deux champs valide si l'offre est valide et message pour le message
    """
    if(not offre.is_actif):
        return {
            "valide":False,
            "detail":f"l'offre {offre.type_offre} {offre.nom} n'est pas disponible"
        }
    elif offre.date_expiration and offre.date_expiration<datetime.today():
        return {
            "valide":False,
            "detail":f"l'offre {offre.type_offre} {offre.nom} n'a expiré"
}
    
    else:
        return {
    "valide":True,
    "detail":"l'abonnement est valide"
}

