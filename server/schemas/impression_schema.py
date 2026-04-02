from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from models.impression import StatutImpression, TypeImpression, OrigineImpression


class ImpressionBase(BaseModel):
    origine: OrigineImpression
    fichier_nom: str
    fichier_path: str
    pages_liste: List[int]
    type_impression: TypeImpression
    recto_verso: bool
    prix_par_page: float
    details: Optional[Dict[str, Any]] = None


class ImpressionCreate(ImpressionBase):
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    poste_id: Optional[int] = None
    achat_id: Optional[int] = None
    operateur_id: Optional[int] = None


class ImpressionUpdate(BaseModel):
    statut: Optional[StatutImpression] = None
    message_erreur: Optional[str] = None


class ImpressionResponse(ImpressionBase):
    id: int
    statut: StatutImpression
    prix_total: float
    pages_total: int
    date_impression: str

    class Config:
        orm_mode = True
