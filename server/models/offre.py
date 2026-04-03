from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import datetime
import enum


class TypeOffre(str, enum.Enum):
    TEMPS = "temps"
    DATA = "data"
    ILLIMITE = "illimite"


class UniteDuree(str, enum.Enum):
    MINUTE = "minute"
    HEURE = "heure"
    JOUR = "jour"
    HEBDO = "hebdo"
    MOIS = "mois"
    ANNEE = "annee"


class Offre(Base):
    __tablename__ = "offre"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)

    type_offre = Column(SqlEnum(TypeOffre), nullable=False)

    debit_upload_kbps = Column(Integer, nullable=True)
    debit_download_kbps = Column(Integer, nullable=True)
    prix = Column(Float, nullable=False)

    date_creation = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=True)

    description = Column(String, nullable=True)
    is_actif = Column(Boolean, default=True)

    # durée générique (pour abonnement, forfait, etc.)
    unite_duree = Column(SqlEnum(UniteDuree), nullable=True)
    valeur_duree = Column(Integer, nullable=True)
    achats = relationship("Achat", back_populates="offre")

    __mapper_args__ = {
        "polymorphic_on": type_offre,
    }


# Offre Temps
class OffreTemps(Offre):
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


def is_valide_offre(offre: Offre) -> dict[str, any]:
    """Vérifie si une offre est valide."""

    if not offre.is_actif:
        return {
            "valide": False,
            "detail": f"L'offre {offre.nom} n'est pas active."
        }

    if offre.date_expiration and offre.date_expiration < datetime.utcnow():
        return {
            "valide": False,
            "detail": f"L'offre {offre.nom} a expiré le {offre.date_expiration.date()}."
        }

    return {
        "valide": True,
        "detail": "L'offre est valide."
    }
