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
