from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.pay_connect_request import PayConnectRequest
from services.pay_connect_service import PayConnectService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(
    prefix="/pay-connect",
    tags=["pay & connect"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize(demande: PayConnectRequest) -> dict:
    return {
        "id": demande.id,
        "poste_id": demande.poste_id,
        "minutes": demande.minutes,
        "montant": demande.montant,
        "statut": demande.statut,
        "operateur_id": demande.operateur_id,
        "date_creation": demande.date_creation,
        "date_traitement": demande.date_traitement,
    }


@router.get("/en-attente")
def en_attente(db: Session = Depends(get_db)):
    return {"status_code": 200, "data": [_serialize(d) for d in PayConnectService.lister_en_attente(db)]}


@router.post("/{request_id}/confirmer")
def confirmer(request_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        demande = PayConnectService.confirmer(db=db, request_id=request_id, operateur_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(demande)}


@router.post("/{request_id}/refuser")
def refuser(request_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        demande = PayConnectService.refuser(db=db, request_id=request_id, operateur_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(demande)}
