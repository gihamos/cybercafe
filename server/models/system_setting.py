from sqlalchemy import (
    Column, Integer, String, DateTime, JSON
)
from datetime import datetime
from config.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Nom unique du paramètre
    cle = Column(String, unique=True, nullable=False)

    # Catégorie (impression, reseau, session, securite, etc.)
    categorie = Column(String, nullable=False)

    # Valeur générique (string, int, float, bool, JSON)
    valeur = Column(JSON, nullable=False)

    # Description lisible
    description = Column(String, nullable=True)

    # Date de mise à jour
    date_modification = Column(DateTime, default=datetime.utcnow)
