from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class UserGroup(Base):
    """Groupe tarifaire/organisationnel de clients (ex: 'Étudiants', 'VIP', 'Scolaire') —
    permet de regrouper et filtrer les comptes, à la manière des groupes d'utilisateurs
    du logiciel de référence. Purement organisationnel pour l'instant : n'affecte pas
    automatiquement la tarification (voir promotion_mechanisms/ pour ça)."""

    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="groupe")
