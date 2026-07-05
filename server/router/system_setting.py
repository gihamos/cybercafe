from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.system_setting import SystemSetting
from schemas.system_setting_schema import SystemSettingCreate, SystemSettingUpdate
from services.system_setting_service import SystemSettingsService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/system-setting",
    tags=["system settings"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin]))]
)


def _serialize(setting: SystemSetting) -> dict:
    return {
        "id": setting.id,
        "cle": setting.cle,
        "categorie": setting.categorie,
        "valeur": setting.valeur,
        "description": setting.description,
        "date_modification": setting.date_modification,
    }


@router.post("/", status_code=201)
def creer_parametre(data: SystemSettingCreate, db: Session = Depends(get_db)):
    try:
        setting = SystemSettingsService.creer_parametre(db=db, **data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(setting)}


@router.get("/categorie/{categorie}")
def get_par_categorie(categorie: str, db: Session = Depends(get_db)):
    settings = SystemSettingsService.get_par_categorie(db=db, categorie=categorie)
    return {"status_code": 200, "data": [_serialize(s) for s in settings]}


@router.get("/{cle}")
def get_parametre(cle: str, db: Session = Depends(get_db)):
    try:
        setting = SystemSettingsService.get_parametre(db=db, cle=cle)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(setting)}


@router.patch("/{cle}")
def update_parametre(cle: str, data: SystemSettingUpdate, db: Session = Depends(get_db)):
    try:
        setting = SystemSettingsService.update_parametre(
            db=db, cle=cle, nouvelle_valeur=data.valeur, description=data.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(setting)}


@router.delete("/{cle}")
def supprimer_parametre(cle: str, db: Session = Depends(get_db)):
    try:
        SystemSettingsService.supprimer_parametre(db=db, cle=cle)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
