from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.database import get_db
from models.fichier_stocke import FichierStocke
from services.Poste_service import PosteService
from services.stockage_service import StockageService, QUOTA_TICKET_MO


router = APIRouter(prefix="/stockage/poste/{poste_id}", tags=["stockage (poste)"])


def _proprietaire_session_active(db: Session, poste_id: int, token: str) -> tuple[int | None, int | None]:
    """Authentifie le poste par son token (même mécanisme que le canal WebSocket, voir
    ws_poste.py) puis résout le propriétaire (compte ou ticket) de la session en cours —
    le kiosk n'a pas de JWT propre, il agit toujours au nom de la session active sur lui."""
    poste = PosteService.authentifier_par_token(db=db, poste_id=poste_id, token=token)
    if not poste:
        raise HTTPException(status_code=401, detail="Poste ou token invalide")

    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session:
        raise HTTPException(status_code=400, detail="Aucune session active sur ce poste")

    return session.user_id, session.ticket_id


def _serialize(fichier: FichierStocke) -> dict:
    return {
        "id": fichier.id,
        "nom_original": fichier.nom_original,
        "taille_octets": fichier.taille_octets,
        "content_type": fichier.content_type,
        "date_upload": fichier.date_upload,
    }


@router.get("/quota")
def quota(poste_id: int, token: str, db: Session = Depends(get_db)):
    user_id, ticket_id = _proprietaire_session_active(db, poste_id, token)

    if user_id is not None:
        quota_mo = StockageService.get_quota_mo(db=db, user_id=user_id)
    else:
        quota_mo = QUOTA_TICKET_MO

    usage_octets = StockageService.get_usage_octets(db=db, user_id=user_id, ticket_id=ticket_id)
    return {"status_code": 200, "data": {"quota_mo": quota_mo, "usage_octets": usage_octets, "temporaire": user_id is None}}


@router.get("/fichiers")
def fichiers(poste_id: int, token: str, db: Session = Depends(get_db)):
    user_id, ticket_id = _proprietaire_session_active(db, poste_id, token)
    liste = StockageService.lister_fichiers(db=db, user_id=user_id, ticket_id=ticket_id)
    return {"status_code": 200, "data": [_serialize(f) for f in liste]}


@router.post("/upload", status_code=201)
async def upload(poste_id: int, token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user_id, ticket_id = _proprietaire_session_active(db, poste_id, token)
    contenu = await file.read()

    try:
        fichier = StockageService.upload_fichier(
            db=db, contenu=contenu, nom_original=file.filename, content_type=file.content_type,
            user_id=user_id, ticket_id=ticket_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(fichier)}


@router.get("/fichiers/{fichier_id}/download")
def download(poste_id: int, fichier_id: int, token: str, db: Session = Depends(get_db)):
    user_id, ticket_id = _proprietaire_session_active(db, poste_id, token)

    try:
        fichier, flux = StockageService.telecharger_fichier(
            db=db, fichier_id=fichier_id, user_id=user_id, ticket_id=ticket_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(
        flux, media_type=fichier.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fichier.nom_original}"'}
    )


@router.delete("/fichiers/{fichier_id}")
def supprimer(poste_id: int, fichier_id: int, token: str, db: Session = Depends(get_db)):
    user_id, ticket_id = _proprietaire_session_active(db, poste_id, token)

    try:
        StockageService.supprimer_fichier(db=db, fichier_id=fichier_id, user_id=user_id, ticket_id=ticket_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": 1}
