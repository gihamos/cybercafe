from sqlalchemy import Column, Integer, Float, String, DateTime, Enum as SqlEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class ModeFiltrage(str, enum.Enum):
    LISTE_NOIRE = "liste_noire"
    LISTE_BLANCHE = "liste_blanche"


class UserGroup(Base):
    """Groupe tarifaire/organisationnel de clients (ex: 'Étudiants', 'VIP', 'Mineurs') —
    un client peut appartenir à plusieurs groupes simultanément. Chaque groupe peut
    porter ses propres limites (bande passante via BandePassanteProfil type='groupe',
    stockage via quota_stockage_mo, filtrage de contenu via SiteRegle) ; lorsqu'un
    client appartient à plusieurs groupes, les limites sont fusionnées de façon
    restrictive (voir services/user_group_service.py::fusionner_limites)."""

    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    # Quota de stockage réseau (Mo) apporté par ce groupe. NULL = pas de limite propre
    # au groupe (voir StockageService pour la fusion avec le quota individuel).
    quota_stockage_mo = Column(Float, nullable=True)

    # Mode de la liste de filtrage de contenu de ce groupe. La liste blanche n'est
    # actuellement enregistrée que côté données/admin : l'application réelle sur le
    # poste (fichier hosts) ne sait bloquer que des domaines explicites, pas
    # "tout sauf X" — un mécanisme de proxy serait nécessaire pour l'appliquer
    # réellement, non construit dans cette itération (voir note dans site_regle_service.py).
    mode_filtrage = Column(SqlEnum(ModeFiltrage), default=ModeFiltrage.LISTE_NOIRE, nullable=False)

    membres = relationship("User", secondary="user_group_members", back_populates="groupes")
