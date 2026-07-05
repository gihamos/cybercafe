from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.app_bloquee import PlateformeApp


class AppBloqueeCreate(BaseModel):
    nom_processus: str
    plateforme: PlateformeApp = PlateformeApp.TOUS
    poste_id: Optional[int] = None
    description: Optional[str] = None


class AppBloqueeUpdate(BaseModel):
    nom_processus: Optional[str] = None
    plateforme: Optional[PlateformeApp] = None
    actif: Optional[bool] = None
    description: Optional[str] = None


class AppBloqueeResponse(BaseModel):
    id: int
    nom_processus: str
    plateforme: PlateformeApp
    poste_id: Optional[int]
    description: Optional[str]
    actif: bool
    date_creation: datetime

    class Config:
        orm_mode = True
