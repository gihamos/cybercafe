from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class PlateformeLecteur(str, enum.Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    TOUS = "tous"


class TypeLecteur(str, enum.Enum):
    AMOVIBLE = "amovible"
    CD_DVD = "cd_dvd"
    RESEAU = "reseau"


class LecteurBloque(Base):
    """Règle de blocage continu par type de lecteur (clé USB, CD/DVD, lecteur réseau) —
    même principe que AppBloquee (blocage de processus) mais pour les périphériques de
    stockage. Le poste applique la règle en continu (voir client/core/drive_manager.py),
    jamais le lecteur système (DRIVE_FIXED) qui n'est structurellement pas concerné par
    ces types."""

    __tablename__ = "lecteurs_bloques"

    id = Column(Integer, primary_key=True, index=True)

    type_lecteur = Column(SqlEnum(TypeLecteur), nullable=False)
    plateforme = Column(SqlEnum(PlateformeLecteur), default=PlateformeLecteur.TOUS)
    description = Column(String, nullable=True)

    # NULL = règle globale (tous les postes) ; sinon spécifique à un poste
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)
    poste = relationship("Poste")

    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
