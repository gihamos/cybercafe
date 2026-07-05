from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class PlateformeApp(str, enum.Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    TOUS = "tous"


class AppBloquee(Base):
    __tablename__ = "apps_bloquees"

    id = Column(Integer, primary_key=True, index=True)

    # Nom du processus tel qu'il apparaît sur le poste (ex: "steam.exe", "chrome")
    nom_processus = Column(String, nullable=False)
    plateforme = Column(SqlEnum(PlateformeApp), default=PlateformeApp.TOUS)
    description = Column(String, nullable=True)

    # NULL = règle globale (tous les postes) ; sinon spécifique à un poste
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)
    poste = relationship("Poste")

    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
