from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.site_regle import SiteRegle
from schemas.site_regle_schema import SiteRegleCreate, SiteRegleUpdate
from services.site_regle_service import SiteRegleService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/site-regle",
    tags=["filtrage de contenu"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize(regle: SiteRegle) -> dict:
    return {
        "id": regle.id,
        "domaine": regle.domaine,
        "description": regle.description,
        "groupe_id": regle.groupe_id,
        "age_min": regle.age_min,
        "actif": regle.actif,
        "date_creation": regle.date_creation,
    }


@router.get("/")
def lister(groupe_id: int | None = None, db: Session = Depends(get_db)):
    return {"status_code": 200, "data": [_serialize(r) for r in SiteRegleService.lister(db=db, groupe_id=groupe_id)]}


@router.post("/", status_code=201)
def creer(data: SiteRegleCreate, db: Session = Depends(get_db)):
    regle = SiteRegleService.creer_regle(
        db=db, domaine=data.domaine, groupe_id=data.groupe_id,
        description=data.description, age_min=data.age_min
    )
    return {"status_code": 201, "data": _serialize(regle)}


@router.patch("/{regle_id}")
def update(regle_id: int, data: SiteRegleUpdate, db: Session = Depends(get_db)):
    try:
        regle = SiteRegleService.update_regle(db=db, regle_id=regle_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(regle)}


@router.delete("/{regle_id}")
def supprimer(regle_id: int, db: Session = Depends(get_db)):
    try:
        SiteRegleService.supprimer_regle(db=db, regle_id=regle_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
