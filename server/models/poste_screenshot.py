from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class PosteScreenshot(Base):
    """Capture d'écran périodique d'un poste pendant une session active — voir
    services/surveillance_service.py. Stockée via le même storage_provider que le
    reste des fichiers (services/storage_provider/), hors quota utilisateur."""

    __tablename__ = "poste_screenshots"

    id = Column(Integer, primary_key=True, index=True)

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    poste = relationship("Poste", backref="screenshots")
    session = relationship("Session", backref="screenshots")

    provider = Column(String, nullable=False, default="local")
    cle_stockage = Column(String, nullable=False)
    taille_octets = Column(Integer, nullable=False)
    content_type = Column(String, nullable=True)

    date_capture = Column(DateTime, default=datetime.utcnow)
