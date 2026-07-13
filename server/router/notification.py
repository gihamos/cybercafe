from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.notification import Notification, TypeNotification
from schemas.notification_schema import NotificationCreate
from services.notification_service import NotificationService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(prefix="/notification", tags=["notifications"], dependencies=[Depends(auth_dependency)])


def _serialize(notif: Notification) -> dict:
    return {
        "id": notif.id,
        "user_id": notif.user_id,
        "ticket_id": notif.ticket_id,
        "poste_id": notif.poste_id,
        "operateur_id": notif.operateur_id,
        "titre": notif.titre,
        "message": notif.message,
        "type_notification": notif.type_notification,
        "est_lue": notif.est_lue,
        "est_envoyee": notif.est_envoyee,
        "date_creation": notif.date_creation,
        "date_lecture": notif.date_lecture,
    }


@router.post("/broadcast", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def diffuser_annonce(
    titre: str,
    message: str,
    cible: str = "tous",  # "postes" | "wifi" | "tous"
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Annonce d'information diffusée aux applications clientes : postes kiosque
    (poussée en direct par WebSocket) et/ou portail WiFi (une seule ligne broadcast,
    toutes cibles NULL, remontée par GET /portail/annonces)."""
    from websocket.manager import manager
    from datetime import datetime

    if cible not in ("postes", "wifi", "tous"):
        raise HTTPException(status_code=400, detail="Cible invalide (postes, wifi ou tous)")
    if not titre.strip() or not message.strip():
        raise HTTPException(status_code=400, detail="Titre et message requis")

    notif = Notification(
        titre=titre.strip(),
        message=message.strip(),
        type_notification=TypeNotification.INFO,
        est_envoyee=True,
        date_envoi=datetime.utcnow(),
        details={"annonce": True, "cible": cible, "operateur_id": currentuser.get("id")},
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    if cible in ("postes", "tous"):
        manager.broadcast_threadsafe("notification", {
            "titre": notif.titre, "message": notif.message, "type": "info",
        })

    return {"status_code": 201, "data": _serialize(notif)}


@router.get("/me")
def mes_notifications(only_unread: bool = False, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = NotificationService.get_user_notifications(db=db, user_id=currentuser.get("id"), only_unread=only_unread)
    return {"status_code": 200, "data": [_serialize(n) for n in notifs]}


@router.patch("/{notif_id}/lue")
def marquer_lue(notif_id: int, db: Session = Depends(get_db)):
    try:
        notif = NotificationService.mark_as_read(db=db, notif_id=notif_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(notif)}


@router.get("/user/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def notifications_user(user_id: int, only_unread: bool = False, db: Session = Depends(get_db)):
    notifs = NotificationService.get_user_notifications(db=db, user_id=user_id, only_unread=only_unread)
    return {"status_code": 200, "data": [_serialize(n) for n in notifs]}


@router.post("/user/{user_id}", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def envoyer_notification_user(user_id: int, data: NotificationCreate, db: Session = Depends(get_db)):
    notif = NotificationService.send_to_user(
        db=db, user_id=user_id, titre=data.titre, message=data.message,
        type_notification=data.type_notification, details=data.details
    )
    return {"status_code": 201, "data": _serialize(notif)}


@router.post("/system", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def envoyer_notification_system(titre: str, message: str, db: Session = Depends(get_db)):
    notif = NotificationService.send_system(db=db, titre=titre, message=message)
    return {"status_code": 201, "data": _serialize(notif)}


@router.post("/expirer", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def expirer_notifications(db: Session = Depends(get_db)):
    count = NotificationService.expire_old_notifications(db=db)
    return {"status_code": 200, "data": {"expirees": count}}
