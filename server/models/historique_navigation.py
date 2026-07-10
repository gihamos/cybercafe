from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class HistoriqueNavigation(Base):
    """Entrée d'historique de navigateur remontée périodiquement depuis un poste (lecture
    locale du fichier d'historique du navigateur, PAS d'interception réseau — voir
    services/surveillance_service.py et client/core/browser_history_reader.py). Un
    même (poste_id, url, date_visite) n'est ingéré qu'une fois : le client renvoie à
    chaque cycle toutes les entrées récentes du fichier, il faut dédupliquer côté
    serveur plutôt que de faire confiance au client pour ne pas répéter."""

    __tablename__ = "historique_navigation"

    id = Column(Integer, primary_key=True, index=True)

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    poste = relationship("Poste", backref="historique_navigation")
    session = relationship("Session", backref="historique_navigation")

    url = Column(String, nullable=False)
    titre = Column(String, nullable=True)
    navigateur = Column(String, nullable=True)  # "chrome", "firefox", "edge"...

    date_visite = Column(DateTime, nullable=False)  # horodatage donné par le navigateur
    date_collecte = Column(DateTime, default=datetime.utcnow)  # quand le serveur l'a reçu

    __table_args__ = (
        UniqueConstraint("poste_id", "url", "date_visite", name="uq_historique_nav_entree"),
    )
