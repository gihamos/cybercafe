from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from services.config_service import ConfigService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/cybercafe", dependencies=[Depends(auth_dependency)])
def get_config(db: Session = Depends(get_db)):
    """Accessible à tout compte authentifié (admin/opérateur/client via le kiosque) :
    le nom/logo/devise servent aussi à l'en-tête des reçus et à l'habillage du client."""
    return {"status_code": 200, "data": ConfigService.get_config(db)}


@router.patch(
    "/cybercafe",
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin]))]
)
def update_config(data: dict, db: Session = Depends(get_db)):
    return {"status_code": 200, "data": ConfigService.update_config(db, data)}
