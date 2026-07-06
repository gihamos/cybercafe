import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from params import JWT_SECRET, ALGORITHM
from models.user import UserRole
from utils.logger import logger
from websocket.manager import manager


router = APIRouter()


@router.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket, token: str):
    """Canal temps réel pour le panneau d'administration (admin/operateur) : le
    navigateur ne peut pas envoyer de header Authorization sur une connexion
    WebSocket, le JWT est donc passé en query param, décodé avec la même logique
    que dependencies/auth.py."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        role = UserRole(payload.get("role"))
    except (jwt.PyJWTError, ValueError):
        await websocket.close(code=4401)
        return

    if role not in (UserRole.admin, UserRole.operateur):
        await websocket.close(code=4403)
        return

    await manager.connect_admin(websocket)
    try:
        while True:
            # rien d'attendu du panneau pour l'instant : on garde la connexion ouverte
            # et on détecte simplement la déconnexion
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Erreur WS admin: {e}")
    finally:
        manager.disconnect_admin(websocket)
