from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
class ConnexionLogBase(BaseModel):
    session_id: int
    poste_id: int
    date_fin: Optional[datetime] = None
    consommation_minutes: int = 0
    consommation_data_mo: float = 0.0


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class ConnexionLogCreate(ConnexionLogBase):
    pass


# ---------------------------------------------------------
# MISE À JOUR
# ---------------------------------------------------------
class ConnexionLogUpdate(BaseModel):
    date_fin: Optional[datetime] = None
    consommation_minutes: Optional[int] = None
    consommation_data_mo: Optional[float] = None


# ---------------------------------------------------------
# RÉPONSE API
# ---------------------------------------------------------
class ConnexionLogResponse(ConnexionLogBase):
    id: int
    date_debut: datetime

    class Config:
        orm_mode = True
