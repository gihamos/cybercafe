from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.app_bloquee import AppBloquee
from schemas.app_bloquee_schema import AppBloqueeCreate, AppBloqueeUpdate
from services.app_bloquee_service import AppBloqueeService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/app-bloquee",
    tags=["applications bloquées"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin]))]
)


def _serialize(regle: AppBloquee) -> dict:
    return {
        "id": regle.id,
        "nom_processus": regle.nom_processus,
        "plateforme": regle.plateforme,
        "poste_id": regle.poste_id,
        "description": regle.description,
        "actif": regle.actif,
        "date_creation": regle.date_creation,
    }


@router.post("/", status_code=201)
def creer_regle(data: AppBloqueeCreate, db: Session = Depends(get_db)):
    regle = AppBloqueeService.creer_regle(db=db, **data.model_dump())
    return {"status_code": 201, "data": _serialize(regle)}


@router.get("/")
def lister_regles(poste_id: int | None = None, db: Session = Depends(get_db)):
    regles = AppBloqueeService.lister(db=db, poste_id=poste_id)
    return {"status_code": 200, "data": [_serialize(r) for r in regles]}


@router.patch("/{regle_id}")
def update_regle(regle_id: int, data: AppBloqueeUpdate, db: Session = Depends(get_db)):
    try:
        regle = AppBloqueeService.update_regle(db=db, regle_id=regle_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(regle)}


@router.delete("/{regle_id}")
def supprimer_regle(regle_id: int, db: Session = Depends(get_db)):
    try:
        AppBloqueeService.supprimer_regle(db=db, regle_id=regle_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
