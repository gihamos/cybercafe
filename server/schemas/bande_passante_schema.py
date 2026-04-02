from pydantic import BaseModel
from typing import Optional
from models.bande_passante import TypeProfilBP


class BandePassanteProfilBase(BaseModel):
    type_profil: TypeProfilBP
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    quota_journalier_mo: Optional[float] = None
    quota_mensuel_mo: Optional[float] = None
    bloquer_si_depasse: bool = False


class BandePassanteProfilCreate(BandePassanteProfilBase):
    offre_id: Optional[int] = None
    abonnement_id: Optional[int] = None
    ticket_id: Optional[int] = None
    user_id: Optional[int] = None
    poste_id: Optional[int] = None


class BandePassanteProfilResponse(BandePassanteProfilBase):
    id: int

    class Config:
        orm_mode = True


class BandePassanteUsageResponse(BaseModel):
    id: int
    session_id: Optional[int]
    user_id: Optional[int]
    ticket_id: Optional[int]
    data_download_mo: float
    data_upload_mo: float
    data_total_mo: float
    date_enregistrement: str

    class Config:
        orm_mode = True
