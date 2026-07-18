from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.lecteur_bloque import PlateformeLecteur, TypeLecteur


class LecteurBloqueCreate(BaseModel):
    type_lecteur: TypeLecteur
    plateforme: PlateformeLecteur = PlateformeLecteur.TOUS
    poste_id: Optional[int] = None
    description: Optional[str] = None


class LecteurBloqueUpdate(BaseModel):
    type_lecteur: Optional[TypeLecteur] = None
    plateforme: Optional[PlateformeLecteur] = None
    actif: Optional[bool] = None
    description: Optional[str] = None


class LecteurBloqueResponse(BaseModel):
    id: int
    type_lecteur: TypeLecteur
    plateforme: PlateformeLecteur
    poste_id: Optional[int]
    description: Optional[str]
    actif: bool
    date_creation: datetime

    class Config:
        orm_mode = True
