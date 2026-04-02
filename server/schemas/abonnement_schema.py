from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class AbonnementBase(BaseModel):
    user_id: int
    achat_id: int
    offre_id: int
    date_fin: Optional[datetime] = None
    est_actif: bool = True
    est_suspendu: bool = False
    minutes_par_jour: Optional[int] = None
    minutes_restantes_aujourdhui: Optional[int] = None
    data_totale_mo: Optional[float] = None
    data_restante_mo: Optional[float] = None
    illimite: bool = False


# ---------------------------------------------------------
# CRÉATION D’UN ABONNEMENT
# ---------------------------------------------------------
class AbonnementCreate(AbonnementBase):
    pass


# ---------------------------------------------------------
# MISE À JOUR D’UN ABONNEMENT
# ---------------------------------------------------------
class AbonnementUpdate(BaseModel):
    date_fin: Optional[datetime] = None
    est_actif: Optional[bool] = None
    est_suspendu: Optional[bool] = None
    minutes_par_jour: Optional[int] = None
    minutes_restantes_aujourdhui: Optional[int] = None
    data_totale_mo: Optional[float] = None
    data_restante_mo: Optional[float] = None
    illimite: Optional[bool] = None


# ---------------------------------------------------------
# RÉPONSE API (lecture)
# ---------------------------------------------------------
class AbonnementResponse(AbonnementBase):
    id: int
    date_debut: datetime

    class Config:
        orm_mode = True
