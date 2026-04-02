from sqlalchemy import Column, Integer, String, Float, Boolean,JSON
from config.database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    description = Column(String, nullable=True)
    prix = Column(Float, nullable=False)
    categorie = Column(String, nullable=True)  # boisson, snack, service, etc.
    actif = Column(Boolean, default=True)
    metadatas=Column(JSON,nullable=True) #ex {images: "lien", longeur :1, largeur :3,poid :10}, ect
