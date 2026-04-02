from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
class AchatArticleBase(BaseModel):
    article_id: int
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    paiement_id: Optional[int] = None
    prix: float


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class AchatArticleCreate(AchatArticleBase):
    pass


# ---------------------------------------------------------
# MISE À JOUR
# ---------------------------------------------------------
class AchatArticleUpdate(BaseModel):
    paiement_id: Optional[int] = None
    prix: Optional[float] = None


# ---------------------------------------------------------
# RÉPONSE API
# ---------------------------------------------------------
class AchatArticleResponse(AchatArticleBase):
    id: int
    date_achat: datetime

    class Config:
        orm_mode = True
