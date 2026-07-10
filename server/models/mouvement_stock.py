from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class TypeMouvementStock(str, enum.Enum):
    ENTREE = "entree"          # réapprovisionnement
    VENTE = "vente"             # décrémenté automatiquement par un achat
    AJUSTEMENT = "ajustement"    # correction manuelle d'inventaire (+/-)


class MouvementStock(Base):
    """Journal d'audit de chaque variation de stock d'un article — vente, réapprovisionnement
    ou ajustement manuel — voir services/article_service.py. Permet de reconstituer
    l'historique complet d'un article plutôt que de ne connaître que son niveau actuel."""

    __tablename__ = "mouvements_stock"

    id = Column(Integer, primary_key=True, index=True)

    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    article = relationship("Article", backref="mouvements_stock")

    type_mouvement = Column(SqlEnum(TypeMouvementStock), nullable=False)
    variation = Column(Integer, nullable=False)  # signé : + entrée/ajustement positif, - vente/ajustement négatif
    stock_apres = Column(Integer, nullable=False)  # niveau de stock résultant, pour audit sans recalcul

    motif = Column(String, nullable=True)

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User")

    date_mouvement = Column(DateTime, default=datetime.utcnow)
