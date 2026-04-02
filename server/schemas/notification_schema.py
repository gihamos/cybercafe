from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from models.notification import TypeNotification


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class NotificationBase(BaseModel):
    titre: str
    message: str
    type_notification: TypeNotification
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    poste_id: Optional[int] = None
    operateur_id: Optional[int] = None
    date_expiration: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class NotificationCreate(NotificationBase):
    est_lue: bool = False
    est_envoyee: bool = False
    est_expiree: bool = False


# ---------------------------------------------------------
# MISE À JOUR
# ---------------------------------------------------------
class NotificationUpdate(BaseModel):
    est_lue: Optional[bool] = None
    est_envoyee: Optional[bool] = None
    est_expiree: Optional[bool] = None
    date_lecture: Optional[datetime] = None
    date_envoi: Optional[datetime] = None
    date_expiration: Optional[datetime] = None


# ---------------------------------------------------------
# RÉPONSE API
# ---------------------------------------------------------
class NotificationResponse(NotificationBase):
    id: int
    est_lue: bool
    est_envoyee: bool
    est_expiree: bool
    date_creation: datetime
    date_envoi: Optional[datetime]
    date_lecture: Optional[datetime]

    class Config:
        orm_mode = True
