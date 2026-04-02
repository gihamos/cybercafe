from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True, index=True)

    # Poste concerné
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)
    poste = relationship("Poste", back_populates="heartbeats")

    # Date du heartbeat
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Statut réseau
    est_en_ligne = Column(Boolean, default=True)
    ip = Column(String, nullable=True)
    mac_adresse = Column(String, nullable=True)

    # Métriques système
    cpu_usage = Column(Float, nullable=True)       # en %
    ram_usage = Column(Float, nullable=True)       # en %
    disk_usage = Column(Float, nullable=True)      # en %
    upload_mbps = Column(Float, nullable=True)
    download_mbps = Column(Float, nullable=True)

    # Version du client
    version_client = Column(String, nullable=True)

    # Uptime du poste
    uptime_seconds = Column(Integer, nullable=True)

    # Erreurs éventuelles
    erreurs = Column(JSON, nullable=True)

    # Commandes envoyées par le serveur
    commande_en_attente = Column(String, nullable=True)
    commande_details = Column(JSON, nullable=True)
