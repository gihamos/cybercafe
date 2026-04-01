from sqlalchemy import (
    Column, Integer, String, Enum as SqlEnum,
    Boolean, DateTime
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
from enum import Enum


class PosteEtat(str, Enum):
    LIBRE = "libre"
    OCCUPE = "occupe"
    BLOQUE = "bloque"
    HORS_LIGNE = "hors_ligne"


class TypePoste(str, Enum):
    CLIENT = "client"
    ADMIN = "admin"
    SERVEUR = "serveur"
    BORNE_WIFI = "borne_wifi"


class Poste(Base):
    __tablename__ = "postes"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    nom = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    # Type de poste
    type_poste = Column(SqlEnum(TypePoste), default=TypePoste.CLIENT)

    # État du poste
    etat = Column(SqlEnum(PosteEtat), default=PosteEtat.BLOQUE)

    # Informations réseau
    ip = Column(String, unique=True, nullable=True)
    mac_adresse = Column(String, unique=True, nullable=True)
    hostname = Column(String, nullable=True)
    os = Column(String, nullable=True)

    # Statut système
    est_verrouille = Column(Boolean, default=True)
    est_en_ligne = Column(Boolean, default=False)

    # Dernière activité (ping, heartbeat)
    derniere_activite = Column(DateTime, default=datetime.utcnow)

    # Version du client installé
    version_client = Column(String, nullable=True)

    # Relations
    sessions = relationship("Session", back_populates="poste")
    connexions = relationship("ConnexionLog", back_populates="poste")
