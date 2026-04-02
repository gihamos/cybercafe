from pydantic import BaseModel
from typing import Optional
from models.poste import PosteEtat, TypePoste


class PosteBase(BaseModel):
    nom: str
    description: Optional[str] = None
    type_poste: Optional[TypePoste] = TypePoste.CLIENT
    ip: Optional[str] = None
    mac_adresse: Optional[str] = None
    hostname: Optional[str] = None
    os: Optional[str] = None


class PosteCreate(PosteBase):
    pass


class PosteUpdate(BaseModel):
    description: Optional[str] = None
    type_poste: Optional[TypePoste] = None
    ip: Optional[str] = None
    mac_adresse: Optional[str] = None
    hostname: Optional[str] = None
    os: Optional[str] = None
    etat: Optional[PosteEtat] = None
    est_verrouille: Optional[bool] = None
    est_en_ligne: Optional[bool] = None


class PosteResponse(PosteBase):
    id: int
    etat: PosteEtat
    est_verrouille: bool
    est_en_ligne: bool
    derniere_activite: str

    class Config:
        orm_mode = True
