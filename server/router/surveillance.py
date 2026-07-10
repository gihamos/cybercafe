from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.poste_screenshot import PosteScreenshot
from models.historique_navigation import HistoriqueNavigation
from services.surveillance_service import SurveillanceService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission


router = APIRouter(
    prefix="/surveillance",
    tags=["surveillance"],
    dependencies=[
        Depends(auth_dependency),
        Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])),
        Depends(require_permission("surveillance")),
    ]
)


def _serialize_capture(c: PosteScreenshot) -> dict:
    return {
        "id": c.id,
        "poste_id": c.poste_id,
        "session_id": c.session_id,
        "taille_octets": c.taille_octets,
        "content_type": c.content_type,
        "date_capture": c.date_capture,
    }


def _serialize_navigation(n: HistoriqueNavigation) -> dict:
    return {
        "id": n.id,
        "poste_id": n.poste_id,
        "session_id": n.session_id,
        "url": n.url,
        "titre": n.titre,
        "navigateur": n.navigateur,
        "date_visite": n.date_visite,
    }


@router.get("/captures")
def lister_captures(
    poste_id: int | None = None, session_id: int | None = None, limit: int = 100, db: Session = Depends(get_db)
):
    captures = SurveillanceService.lister_captures(db=db, poste_id=poste_id, session_id=session_id, limit=limit)
    return {"status_code": 200, "data": [_serialize_capture(c) for c in captures]}


@router.get("/captures/{capture_id}/image")
def telecharger_capture(capture_id: int, db: Session = Depends(get_db)):
    try:
        capture, flux = SurveillanceService.get_capture(db, capture_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(flux, media_type=capture.content_type or "image/png")


@router.delete("/captures/{capture_id}")
def supprimer_capture(capture_id: int, db: Session = Depends(get_db)):
    try:
        SurveillanceService.supprimer_capture(db, capture_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status_code": 200, "data": 1}


@router.get("/historique")
def lister_historique(
    poste_id: int | None = None,
    session_id: int | None = None,
    user_id: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    entrees = SurveillanceService.lister_historique(
        db=db, poste_id=poste_id, session_id=session_id, user_id=user_id, limit=limit
    )
    return {"status_code": 200, "data": [_serialize_navigation(n) for n in entrees]}
