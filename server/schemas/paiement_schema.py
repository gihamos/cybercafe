from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from models.paiement import TypePaiement


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
class PaiementBase(BaseModel):
    montant: float
    type_paiement: TypePaiement
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class PaiementCreate(PaiementBase):
    pass


# ---------------------------------------------------------
# MISE À JOUR
# ---------------------------------------------------------
class PaiementUpdate(BaseModel):
    statut: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------
# RÉPONSE API
# ---------------------------------------------------------
class PaiementResponse(PaiementBase):
    id: int
    statut: str
    date_paiement: datetime

    class Config:
        orm_mode = True
