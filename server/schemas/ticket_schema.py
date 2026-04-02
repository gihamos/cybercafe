from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.ticket import TypeTicket


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class TicketBase(BaseModel):
    code: str
    description: Optional[str] = None
    type_ticket: TypeTicket
    date_expiration: Optional[datetime] = None
    offre_id: Optional[int] = None


# ---------------------------------------------------------
# CRÉATION D’UN TICKET
# ---------------------------------------------------------
class TicketCreate(TicketBase):
    est_actif: bool = True
    est_consomme: bool = False
    restant_minutes: Optional[int] = None
    restant_data_mo: Optional[float] = None


# ---------------------------------------------------------
# MISE À JOUR D’UN TICKET
# ---------------------------------------------------------
class TicketUpdate(BaseModel):
    description: Optional[str] = None
    date_expiration: Optional[datetime] = None
    est_actif: Optional[bool] = None
    est_consomme: Optional[bool] = None
    restant_minutes: Optional[int] = None
    restant_data_mo: Optional[float] = None


# ---------------------------------------------------------
# RÉPONSE API (lecture)
# ---------------------------------------------------------
class TicketResponse(TicketBase):
    id: int
    date_achat: datetime
    est_actif: bool
    est_consomme: bool
    restant_minutes: Optional[int]
    restant_data_mo: Optional[float]

    class Config:
        orm_mode = True
