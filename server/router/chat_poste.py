from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.database import get_db
from models.chat_message import ChatMessage, ExpediteurChat
from services.Poste_service import PosteService
from services.chat_service import ChatService
from websocket.manager import manager


router = APIRouter(prefix="/chat-poste/{poste_id}", tags=["chat (poste)"])


def _authentifier(db: Session, poste_id: int, token: str) -> None:
    """Même mécanisme d'authentification par token que le canal WebSocket et l'espace
    de stockage réseau côté poste (voir ws_poste.py / stockage_poste.py) — le kiosk n'a
    pas de JWT propre."""
    poste = PosteService.authentifier_par_token(db=db, poste_id=poste_id, token=token)
    if not poste:
        raise HTTPException(status_code=401, detail="Poste ou token invalide")


def _serialize(msg: ChatMessage) -> dict:
    return {
        "id": msg.id,
        "poste_id": msg.poste_id,
        "expediteur": msg.expediteur.value,
        "operateur_id": msg.operateur_id,
        "message": msg.message,
        "date_envoi": msg.date_envoi.isoformat(),
        "lu": msg.lu,
        "piece_jointe_nom": msg.piece_jointe_nom,
        "piece_jointe_taille_octets": msg.piece_jointe_taille_octets,
        "piece_jointe_content_type": msg.piece_jointe_content_type,
    }


@router.post("/message-fichier", status_code=201)
async def envoyer_message_avec_fichier(
    poste_id: int, token: str,
    message: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _authentifier(db, poste_id, token)
    contenu = await file.read()

    try:
        msg = ChatService.envoyer_message_client(
            db=db, poste_id=poste_id, message=message,
            fichier=(contenu, file.filename, file.content_type),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    payload = _serialize(msg)
    manager.broadcast_to_admins_threadsafe("chat_message", payload)

    return {"status_code": 201, "data": payload}


@router.get("/message/{message_id}/piece-jointe")
def telecharger_piece_jointe(poste_id: int, message_id: int, token: str, db: Session = Depends(get_db)):
    _authentifier(db, poste_id, token)

    try:
        msg, flux = ChatService.get_piece_jointe(db, message_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if msg.poste_id != poste_id:
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable")

    return StreamingResponse(
        flux, media_type=msg.piece_jointe_content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{msg.piece_jointe_nom}"'}
    )
