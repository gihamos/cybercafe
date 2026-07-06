from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class PromotionCreate(BaseModel):
    nom: str
    mecanisme: str = "pourcentage"
    valeur: float
    code: Optional[str] = None
    offre_id: Optional[int] = None
    article_id: Optional[int] = None
    date_fin: Optional[datetime] = None
    usage_max: Optional[int] = None
    parametres: Optional[Dict[str, Any]] = None


class PromotionUpdate(BaseModel):
    nom: Optional[str] = None
    mecanisme: Optional[str] = None
    valeur: Optional[float] = None
    date_fin: Optional[datetime] = None
    usage_max: Optional[int] = None
    parametres: Optional[Dict[str, Any]] = None
    actif: Optional[bool] = None


class PromotionResponse(BaseModel):
    id: int
    nom: str
    code: Optional[str]
    mecanisme: str
    valeur: float
    parametres: Optional[Dict[str, Any]]
    offre_id: Optional[int]
    article_id: Optional[int]
    date_debut: datetime
    date_fin: Optional[datetime]
    usage_max: Optional[int]
    usage_count: int
    actif: bool
    date_creation: datetime

    class Config:
        orm_mode = True
