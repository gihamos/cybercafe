from pydantic import BaseModel
from typing import Optional, Dict, Any


class ArticleBase(BaseModel):
    nom: str
    description: Optional[str] = None
    prix: float
    categorie: Optional[str] = None
    metadatas: Optional[Dict[str, Any]] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    prix: Optional[float] = None
    categorie: Optional[str] = None
    actif: Optional[bool] = None
    metadatas: Optional[Dict[str, Any]] = None


class ArticleResponse(ArticleBase):
    id: int
    actif: bool

    class Config:
        orm_mode = True
