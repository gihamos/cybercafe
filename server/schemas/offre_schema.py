from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.offre import TypeOffre, UniteDuree


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class OffreBase(BaseModel):
    nom: str
    type_offre: TypeOffre
    prix: float
    description: Optional[str] = None
    debit_upload_kbps: Optional[int] = None
    debit_download_kbps: Optional[int] = None
    date_expiration: Optional[datetime] = None
    unite_duree: Optional[UniteDuree] = None
    valeur_duree: Optional[int] = None


# ---------------------------------------------------------
# CRÉATION D’UNE OFFRE
# ---------------------------------------------------------
class OffreCreate(OffreBase):
    is_actif: bool = True


# ---------------------------------------------------------
# MISE À JOUR D’UNE OFFRE
# ---------------------------------------------------------
class OffreUpdate(BaseModel):
    nom: Optional[str] = None
    prix: Optional[float] = None
    description: Optional[str] = None
    debit_upload_kbps: Optional[int] = None
    debit_download_kbps: Optional[int] = None
    date_expiration: Optional[datetime] = None
    is_actif: Optional[bool] = None
    unite_duree: Optional[UniteDuree] = None
    valeur_duree: Optional[int] = None


# ---------------------------------------------------------
# RÉPONSE API (lecture)
# ---------------------------------------------------------
class OffreResponse(OffreBase):
    id: int
    is_actif: bool
    date_creation: datetime

    class Config:
        orm_mode = True


# ---------------------------------------------------------
# RÉPONSES SPÉCIFIQUES SELON LE TYPE D’OFFRE
# ---------------------------------------------------------
class OffreTempsResponse(OffreResponse):
    duree_minutes: int


class OffreDataResponse(OffreResponse):
    quota_mo: float


class OffreIllimiteResponse(OffreResponse):
    pass
