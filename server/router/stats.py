from fastapi import APIRouter, Depends
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
