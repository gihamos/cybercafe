from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .connexion_log_schema import ConnexionLogResponse


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
class SessionBase(BaseModel):
    poste_id: int
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    abonnement_id: Optional[int] = None
    achat_id: Optional[int] = None


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class SessionCreate(SessionBase):
    pass


# ---------------------------------------------------------
# MISE À JOUR
# ---------------------------------------------------------
class SessionUpdate(BaseModel):
    est_active: Optional[bool] = None
    est_terminee: Optional[bool] = None
    consommation_minutes: Optional[int] = None
    consommation_data_mo: Optional[float] = None
    date_fin: Optional[datetime] = None


# ---------------------------------------------------------
# RÉPONSE SIMPLE
# ---------------------------------------------------------
class SessionResponse(SessionBase):
    id: int
    date_debut: datetime
    date_fin: Optional[datetime]
    est_active: bool
    est_terminee: bool
    consommation_minutes: int
    consommation_data_mo: float
    limite_minutes: Optional[int]
    limite_data_mo: Optional[float]

    class Config:
        orm_mode = True


# ---------------------------------------------------------
# RÉPONSE COMPLÈTE (AVEC CONNEXIONS)
# ---------------------------------------------------------
class SessionFullResponse(SessionResponse):
    connexions: List[ConnexionLogResponse] = []
