from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, ForeignKey
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
