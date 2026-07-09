from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class SiteRegle(Base):
    """Règle de filtrage de contenu (domaine bloqué), appliquée par groupe de clients —
    NULL = règle globale (tous les clients, y compris sans groupe). Le poste applique le
    blocage via son fichier hosts (voir client/core/hosts_manager.py), même principe que
    le blocage de processus (AppBloquee) mais pour la navigation web."""

    __tablename__ = "site_regles"

    id = Column(Integer, primary_key=True, index=True)

    domaine = Column(String, nullable=False)
    description = Column(String, nullable=True)

    groupe_id = Column(Integer, ForeignKey("user_groups.id"), nullable=True)
    groupe = relationship("UserGroup")

    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
