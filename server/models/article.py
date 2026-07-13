from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from config.database import Base
from models.article_categorie import ArticleCategorie

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    description = Column(String, nullable=True)
    prix = Column(Float, nullable=False)
    categorie_id = Column(Integer, ForeignKey("article_categories.id"), nullable=True)
    categorie = relationship("ArticleCategorie", back_populates="articles")
    actif = Column(Boolean, default=True)
    metadatas=Column(JSON,nullable=True) #ex {images: "lien", longeur :1, largeur :3,poid :10}, ect

    # Fiche produit : code unique d'identification (SKU, auto-généré si absent),
    # code-barres (lecture scanner en caisse), conservation et informations
    # détaillées (origine, ingrédients, poids, allergènes).
    sku = Column(String, nullable=True, unique=True, index=True)
    # "non_perissable" | "perissable" | "frais" — les produits frais ne sont
    # jamais remboursables (voir services/vente_caisse_service.py)
    type_conservation = Column(String, default="non_perissable")
    code_barre = Column(String, nullable=True, index=True)
    date_peremption = Column(Date, nullable=True)
    origine = Column(String, nullable=True)
    ingredients = Column(String, nullable=True)
    poids_grammes = Column(Float, nullable=True)
    allergenes = Column(String, nullable=True)

    # Gestion de stock. NULL = stock non suivi (service, ou article toujours disponible).
    stock = Column(Integer, nullable=True)
    stock_alerte = Column(Integer, nullable=True)

    # Image réelle de l'article (remplace l'emoji de catégorie dans l'affichage quand
    # elle est définie) — stockée via services/storage_provider/, voir router/article.py.
    image_cle_stockage = Column(String, nullable=True)
    image_content_type = Column(String, nullable=True)
