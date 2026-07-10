from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.user_group import UserGroup
from schemas.user_schema import UserGroupCreate, UserGroupUpdate
from services.user_group_service import UserGroupService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission


router = APIRouter(
    prefix="/user-group",
    tags=["groupes utilisateurs"],
    dependencies=[
        Depends(auth_dependency),
        Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])),
        Depends(require_permission("clients")),
    ]
)


def _serialize(groupe: UserGroup) -> dict:
    return {
        "id": groupe.id,
        "nom": groupe.nom,
        "description": groupe.description,
        "date_creation": groupe.date_creation,
        "mode_filtrage": groupe.mode_filtrage,
        "quota_stockage_mo": groupe.quota_stockage_mo,
        "nb_membres": len(groupe.membres),
    }


@router.get("/")
def lister(db: Session = Depends(get_db)):
    return {"status_code": 200, "data": [_serialize(g) for g in UserGroupService.lister(db)]}


@router.post("/", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def creer(data: UserGroupCreate, db: Session = Depends(get_db)):
    try:
        groupe = UserGroupService.creer(
            db=db, nom=data.nom, description=data.description,
            mode_filtrage=data.mode_filtrage, quota_stockage_mo=data.quota_stockage_mo
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(groupe)}


@router.post("/{groupe_id}/membres/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def ajouter_membre(groupe_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        groupe = UserGroupService.ajouter_membre(db=db, groupe_id=groupe_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(groupe)}


@router.delete("/{groupe_id}/membres/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def retirer_membre(groupe_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        groupe = UserGroupService.retirer_membre(db=db, groupe_id=groupe_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(groupe)}


@router.patch("/{groupe_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update(groupe_id: int, data: UserGroupUpdate, db: Session = Depends(get_db)):
    try:
        groupe = UserGroupService.update(db=db, groupe_id=groupe_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(groupe)}


@router.delete("/{groupe_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def supprimer(groupe_id: int, db: Session = Depends(get_db)):
    try:
        UserGroupService.supprimer(db=db, groupe_id=groupe_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
