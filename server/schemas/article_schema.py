from datetime import date
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ArticleBase(BaseModel):
    nom: str
    description: Optional[str] = None
    prix: float
    categorie_id: Optional[int] = None
    metadatas: Optional[Dict[str, Any]] = None
    stock: Optional[int] = None
    stock_alerte: Optional[int] = None
    code_barre: Optional[str] = None
    date_peremption: Optional[date] = None
    origine: Optional[str] = None
    ingredients: Optional[str] = None
    poids_grammes: Optional[float] = None
    allergenes: Optional[str] = None
    type_conservation: Optional[str] = None
    sku: Optional[str] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    prix: Optional[float] = None
    categorie_id: Optional[int] = None
    actif: Optional[bool] = None
    metadatas: Optional[Dict[str, Any]] = None
    stock: Optional[int] = None
    stock_alerte: Optional[int] = None
    code_barre: Optional[str] = None
    date_peremption: Optional[date] = None
    origine: Optional[str] = None
    ingredients: Optional[str] = None
    poids_grammes: Optional[float] = None
    allergenes: Optional[str] = None
    type_conservation: Optional[str] = None
    sku: Optional[str] = None


class ArticleResponse(ArticleBase):
    id: int
    actif: bool

    class Config:
        orm_mode = True


class ArticleCategorieCreate(BaseModel):
    nom: str
    emoji: Optional[str] = None
    description: Optional[str] = None


class ArticleCategorieUpdate(BaseModel):
    nom: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None
