from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class ArticleCategorie(Base):
    """Catégorie d'articles de la boutique (ex: '🥤 Boissons', '🍫 Snacks', '🖨️ Services')
    — l'emoji sert d'icône visuelle rapide dans la boutique du kiosque et le panneau
    d'administration, sans dépendre d'une bibliothèque d'icônes ou d'images uploadées."""

    __tablename__ = "article_categories"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)
    emoji = Column(String, nullable=True)

    # Image de la catégorie (remplace l'emoji dans les interfaces quand définie)
    image_cle_stockage = Column(String, nullable=True)
    image_content_type = Column(String, nullable=True)
    description = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    articles = relationship("Article", back_populates="categorie")
