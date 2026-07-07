from pydantic import BaseModel
from datetime import datetime
from models.chat_message import ExpediteurChat


class ChatMessageCreate(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    id: int
    poste_id: int
    expediteur: ExpediteurChat
    operateur_id: int | None
    message: str
    date_envoi: datetime
    lu: bool

    class Config:
        orm_mode = True
