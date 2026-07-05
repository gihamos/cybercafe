from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.historique import Historique
from services.historique_service import HistoriqueService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/historique",
    tags=["historique"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize(entry: Historique) -> dict:
    return {
        "id": entry.id,
        "type_evenement": entry.type_evenement,
        "description": entry.description,
        "details": entry.details,
        "user_id": entry.user_id,
        "operateur_id": entry.operateur_id,
        "ticket_id": entry.ticket_id,
        "poste_id": entry.poste_id,
        "timestamp": entry.timestamp,
    }


@router.get("/")
def get_all(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    entries = HistoriqueService.get_all(db=db, limit=limit, offset=offset)
    return {"status_code": 200, "data": [_serialize(e) for e in entries]}


@router.get("/user/{user_id}")
def get_by_user(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    entries = HistoriqueService.get_by_user(db=db, user_id=user_id, limit=limit)
    return {"status_code": 200, "data": [_serialize(e) for e in entries]}


@router.get("/poste/{poste_id}")
def get_by_poste(poste_id: int, limit: int = 100, db: Session = Depends(get_db)):
    entries = HistoriqueService.get_by_poste(db=db, poste_id=poste_id, limit=limit)
    return {"status_code": 200, "data": [_serialize(e) for e in entries]}


@router.get("/ticket/{ticket_id}")
def get_by_ticket(ticket_id: int, limit: int = 100, db: Session = Depends(get_db)):
    entries = HistoriqueService.get_by_ticket(db=db, ticket_id=ticket_id, limit=limit)
    return {"status_code": 200, "data": [_serialize(e) for e in entries]}


@router.delete("/purge", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def purge(days: int = 30, db: Session = Depends(get_db)):
    deleted = HistoriqueService.purge(db=db, days=days)
    return {"status_code": 200, "data": {"supprimes": deleted}}
