from sqlalchemy import Column, String, Integer, Float, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import date
import enum
from sqlalchemy import Enum as SqlEnum


class TypeOffre(str, enum.Enum):
    TEMPS = "temps"
    DATA = "data"
    ILLIMITE = "illimite"


class Offre(Base):
    __tablename__ = "offre"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)

    type_offre = Column(SqlEnum(TypeOffre), nullable=False)

    debit_kbps = Column(Integer, nullable=True)
    prix = Column(Float, nullable=False)

    date_creation = Column(Date, default=date.today)
    date_expiration = Column(Date, nullable=True)

    description = Column(String, nullable=True)
    actif = Column(Boolean, default=True)


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