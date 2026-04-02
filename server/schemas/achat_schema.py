from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class AchatBase(BaseModel):
    user_id: int
    operateur_id: int
    offre_id: Optional[int] = None
    ticket_id: Optional[int] = None
    abonnement_id: Optional[int] = None
    prix_paye: float
    date_expiration: Optional[datetime] = None


# ---------------------------------------------------------
# CRÉATION D’UN ACHAT
# ---------------------------------------------------------
class AchatCreate(AchatBase):
    est_actif: bool = True
    est_consomme: bool = False
    minutes_restantes: Optional[int] = None
    data_restante_mo: Optional[float] = None


# ---------------------------------------------------------
# MISE À JOUR D’UN ACHAT
# ---------------------------------------------------------
class AchatUpdate(BaseModel):
    est_actif: Optional[bool] = None
    est_consomme: Optional[bool] = None
    date_expiration: Optional[datetime] = None
    minutes_restantes: Optional[int] = None
    data_restante_mo: Optional[float] = None


# ---------------------------------------------------------
# RÉPONSE API (lecture)
# ---------------------------------------------------------
class AchatResponse(AchatBase):
    id: int
    est_actif: bool
    est_consomme: bool
    minutes_restantes: Optional[int]
    data_restante_mo: Optional[float]
    date_achat: datetime

    class Config:
        orm_mode = True
