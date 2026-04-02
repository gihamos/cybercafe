from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from models.historique import TypeEvenement


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
class HistoriqueBase(BaseModel):
    type_evenement: TypeEvenement
    description: str
    details: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    operateur_id: Optional[int] = None
    poste_id: Optional[int] = None


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class HistoriqueCreate(HistoriqueBase):
    pass


# ---------------------------------------------------------
# RÉPONSE API
# ---------------------------------------------------------
class HistoriqueResponse(HistoriqueBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
