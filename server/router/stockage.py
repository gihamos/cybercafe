from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import User, UserRole
from models.fichier_stocke import FichierStocke
from schemas.stockage_schema import QuotaUpdate
from services.stockage_service import StockageService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(
    prefix="/stockage",
    tags=["stockage"],
    dependencies=[Depends(auth_dependency)]
)


def _serialize(fichier: FichierStocke) -> dict:
    return {
        "id": fichier.id,
        "nom_original": fichier.nom_original,
        "taille_octets": fichier.taille_octets,
        "content_type": fichier.content_type,
        "date_upload": fichier.date_upload,
    }


@router.get("/quota")
def ma_quota(db: Session = Depends(get_db), user=Depends(get_current_user)):
    quota_mo = StockageService.get_quota_mo(db=db, user_id=user["id"])
    usage_octets = StockageService.get_usage_octets(db=db, user_id=user["id"])
    return {"status_code": 200, "data": {"quota_mo": quota_mo, "usage_octets": usage_octets}}


@router.get("/fichiers")
def mes_fichiers(db: Session = Depends(get_db), user=Depends(get_current_user)):
    fichiers = StockageService.lister_fichiers(db=db, user_id=user["id"])
    return {"status_code": 200, "data": [_serialize(f) for f in fichiers]}


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    contenu = await file.read()
    try:
        fichier = StockageService.upload_fichier(
            db=db, contenu=contenu, nom_original=file.filename,
            content_type=file.content_type, user_id=user["id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(fichier)}


@router.get("/fichiers/{fichier_id}/download")
def download(fichier_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        fichier, flux = StockageService.telecharger_fichier(db=db, fichier_id=fichier_id, user_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(
        flux, media_type=fichier.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fichier.nom_original}"'}
    )


@router.delete("/fichiers/{fichier_id}")
def supprimer(fichier_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        StockageService.supprimer_fichier(db=db, fichier_id=fichier_id, user_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": 1}


# ---------------------------------------------------------
# GESTION DES QUOTAS (admin uniquement)
# ---------------------------------------------------------
@router.get("/quota/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def quota_utilisateur(user_id: int, db: Session = Depends(get_db)):
    try:
        quota_mo = StockageService.get_quota_mo(db=db, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    usage_octets = StockageService.get_usage_octets(db=db, user_id=user_id)
    return {"status_code": 200, "data": {"quota_mo": quota_mo, "usage_octets": usage_octets}}


@router.patch("/quota/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def modifier_quota(user_id: int, data: QuotaUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        StockageService.set_quota(db=db, user_id=user_id, quota_mo=data.quota_stockage_mo, operateur_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": 1}
