from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.chat_message import ChatMessage, ExpediteurChat
from models.poste import Poste
from schemas.chat_schema import ChatMessageCreate
from services.chat_service import ChatService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user
from websocket.manager import manager


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize(msg: ChatMessage) -> dict:
    return {
        "id": msg.id,
        "poste_id": msg.poste_id,
        "expediteur": msg.expediteur.value,
        "operateur_id": msg.operateur_id,
        "message": msg.message,
        "date_envoi": msg.date_envoi.isoformat(),
        "lu": msg.lu,
    }


@router.get("/non-lus")
def non_lus(db: Session = Depends(get_db)):
    return {"status_code": 200, "data": ChatService.compter_non_lus_par_poste(db)}


@router.get("/poste/{poste_id}")
def historique(poste_id: int, db: Session = Depends(get_db)):
    messages = ChatService.historique(db=db, poste_id=poste_id)
    ChatService.marquer_lu(db=db, poste_id=poste_id, expediteur_a_marquer=ExpediteurChat.CLIENT)
    return {"status_code": 200, "data": [_serialize(m) for m in messages]}


@router.post("/poste/{poste_id}/message", status_code=201)
def envoyer_message(poste_id: int, data: ChatMessageCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not db.query(Poste).get(poste_id):
        raise HTTPException(status_code=404, detail="Poste introuvable")

    msg = ChatService.envoyer_message_operateur(
        db=db, poste_id=poste_id, operateur_id=user["id"], message=data.message
    )
    payload = _serialize(msg)

    manager.send_to_poste_threadsafe(poste_id, "chat_message", payload)
    manager.broadcast_to_admins_threadsafe("chat_message", payload)

    return {"status_code": 201, "data": payload}
