from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from services.stats_service import StatsService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/stats",
    tags=["statistiques"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


@router.get("/resume")
def resume(db: Session = Depends(get_db)):
    return {"status_code": 200, "data": StatsService.resume(db)}


@router.get("/detaille")
def detaille(
    date_debut: datetime | None = None,
    date_fin: datetime | None = None,
    db: Session = Depends(get_db)
):
    if date_fin is None:
        date_fin = datetime.utcnow()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=30)
    if date_debut >= date_fin:
        raise HTTPException(status_code=400, detail="date_debut doit être antérieure à date_fin")

    return {"status_code": 200, "data": StatsService.detaille(db, date_debut, date_fin)}
