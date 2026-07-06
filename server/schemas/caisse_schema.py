from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CaisseOuvrir(BaseModel):
    montant_ouverture: float = 0


class CaisseCloturer(BaseModel):
    montant_cloture_reel: float
    notes: Optional[str] = None


class CaisseResponse(BaseModel):
    id: int
    operateur_id: int
    montant_ouverture: float
    date_ouverture: datetime
    montant_cloture_theorique: Optional[float]
    montant_cloture_reel: Optional[float]
    ecart: Optional[float]
    date_cloture: Optional[datetime]
    est_ouverte: bool
    notes: Optional[str]

    class Config:
        orm_mode = True
