from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.offre import Offre, TypeOffre
from schemas.offre_schema import OffreCreate, OffreUpdate
from services.offre_service import OffreService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission


router = APIRouter(prefix="/offre", tags=["offres"], dependencies=[Depends(auth_dependency)])


def _serialize(offre: Offre) -> dict:
    data = {
        "id": offre.id,
        "nom": offre.nom,
        "type_offre": offre.type_offre,
        "prix": offre.prix,
        "description": offre.description,
        "debit_upload_kbps": offre.debit_upload_kbps,
        "debit_download_kbps": offre.debit_download_kbps,
        "unite_duree": offre.unite_duree,
        "valeur_duree": offre.valeur_duree,
        "is_actif": offre.is_actif,
        "date_creation": offre.date_creation,
        "date_expiration": offre.date_expiration,
        "max_sessions_simultanees": offre.max_sessions_simultanees,
    }
    if hasattr(offre, "duree_minutes"):
        data["duree_minutes"] = offre.duree_minutes
    if hasattr(offre, "quota_mo"):
        data["quota_mo"] = offre.quota_mo
    return data


@router.post("/", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("creation_forfaits"))])
def creer_offre(data: OffreCreate, db: Session = Depends(get_db)):
    try:
        offre = OffreService.creer_offre(db=db, data=data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(offre)}


@router.get("/")
def rechercher_offres(
    type_offre: TypeOffre | None = None,
    is_actif: bool | None = None,
    nom: str | None = None,
    db: Session = Depends(get_db)
):
    offres = OffreService.rechercher_offres(db=db, type_offre=type_offre, is_actif=is_actif, nom=nom)
    return {"status_code": 200, "data": [_serialize(o) for o in offres]}


@router.get("/{offre_id}")
def get_offre(offre_id: int, db: Session = Depends(get_db)):
    try:
        offre = OffreService.get_by_id(db, offre_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(offre)}


@router.patch("/{offre_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("creation_forfaits"))])
def update_offre(offre_id: int, data: OffreUpdate, db: Session = Depends(get_db)):
    try:
        offre = OffreService.update_offre(db=db, offre_id=offre_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(offre)}


@router.patch("/{offre_id}/actif", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("creation_forfaits"))])
def set_actif(offre_id: int, actif: bool, db: Session = Depends(get_db)):
    try:
        offre = OffreService.set_actif(db=db, offre_id=offre_id, actif=actif)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(offre)}


@router.delete("/{offre_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("creation_forfaits"))])
def supprimer_offre(offre_id: int, db: Session = Depends(get_db)):
    try:
        OffreService.supprimer_offre(db=db, offre_id=offre_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
