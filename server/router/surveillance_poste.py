from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from config.database import get_db
from services.Poste_service import PosteService
from services.surveillance_service import SurveillanceService
from services.config_service import ConfigService


router = APIRouter(prefix="/surveillance-poste/{poste_id}", tags=["surveillance (poste)"])


def _authentifier(db: Session, poste_id: int, token: str) -> None:
    """Même mécanisme d'authentification par token que le reste des endpoints poste
    (voir chat_poste.py / stockage_poste.py) — le kiosk n'a pas de JWT propre."""
    poste = PosteService.authentifier_par_token(db=db, poste_id=poste_id, token=token)
    if not poste:
        raise HTTPException(status_code=401, detail="Poste ou token invalide")


def _session_active_id(db: Session, poste_id: int) -> int | None:
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    return session.id if session else None


@router.get("/config")
def config(poste_id: int, token: str, db: Session = Depends(get_db)):
    _authentifier(db, poste_id, token)
    cfg = ConfigService.get_config(db)
    return {
        "status_code": 200,
        "data": {
            "captures_actif": cfg.get("surveillance.captures_actif", True),
            "captures_intervalle_secondes": cfg.get("surveillance.captures_intervalle_secondes", 300),
            "historique_actif": cfg.get("surveillance.historique_actif", True),
            "historique_intervalle_secondes": cfg.get("surveillance.historique_intervalle_secondes", 300),
        },
    }


@router.post("/capture", status_code=201)
async def envoyer_capture(poste_id: int, token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _authentifier(db, poste_id, token)
    contenu = await file.read()

    try:
        capture = SurveillanceService.enregistrer_capture(
            db=db, poste_id=poste_id, contenu=contenu, content_type=file.content_type,
            session_id=_session_active_id(db, poste_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": {"id": capture.id}}


@router.post("/historique", status_code=201)
def envoyer_historique(poste_id: int, token: str, entrees: list[dict], db: Session = Depends(get_db)):
    _authentifier(db, poste_id, token)

    try:
        nb = SurveillanceService.enregistrer_entrees(
            db=db, poste_id=poste_id, entrees=entrees, session_id=_session_active_id(db, poste_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": {"inserees": nb}}
