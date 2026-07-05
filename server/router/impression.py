from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.impression import Impression, StatutImpression, OrigineImpression
from models.paiement import TypePaiement
from schemas.impression_schema import ImpressionCreate
from services.impression_service import ImpressionService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(prefix="/impression", tags=["impressions"], dependencies=[Depends(auth_dependency)])


def _serialize(impression: Impression) -> dict:
    return {
        "id": impression.id,
        "origine": impression.origine,
        "user_id": impression.user_id,
        "ticket_id": impression.ticket_id,
        "poste_id": impression.poste_id,
        "fichier_nom": impression.fichier_nom,
        "pages_total": impression.pages_total,
        "recto_verso": impression.recto_verso,
        "type_impression": impression.type_impression,
        "prix_par_page": impression.prix_par_page,
        "prix_total": impression.prix_total,
        "statut": impression.statut,
        "message_erreur": impression.message_erreur,
        "date_impression": impression.date_impression,
    }


@router.post("/", status_code=201)
def creer_impression(data: ImpressionCreate, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload.setdefault("user_id", currentuser.get("id"))
    try:
        impression = ImpressionService.creer_impression(db=db, **payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(impression)}


@router.get("/", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def rechercher_impressions(
    user_id: int | None = None,
    ticket_id: int | None = None,
    poste_id: int | None = None,
    statut: StatutImpression | None = None,
    origine: OrigineImpression | None = None,
    db: Session = Depends(get_db)
):
    impressions = ImpressionService.rechercher_impressions(
        db=db, user_id=user_id, ticket_id=ticket_id, poste_id=poste_id, statut=statut, origine=origine
    )
    return {"status_code": 200, "data": [_serialize(i) for i in impressions]}


@router.post("/{impression_id}/payer", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def payer_impression(impression_id: int, utiliser_solde: bool = False, type_paiement: TypePaiement | None = None, db: Session = Depends(get_db)):
    try:
        impression = ImpressionService.payer_impression(
            db=db, impression_id=impression_id, utiliser_solde=utiliser_solde, type_paiement=type_paiement
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(impression)}


@router.post("/{impression_id}/demarrer", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def demarrer_impression(impression_id: int, db: Session = Depends(get_db)):
    try:
        impression = ImpressionService.demarrer_impression(db=db, impression_id=impression_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(impression)}


@router.post("/{impression_id}/terminer", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def terminer_impression(impression_id: int, db: Session = Depends(get_db)):
    try:
        impression = ImpressionService.terminer_impression(db=db, impression_id=impression_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(impression)}


@router.post("/{impression_id}/erreur", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def erreur_impression(impression_id: int, message: str, db: Session = Depends(get_db)):
    try:
        impression = ImpressionService.erreur_impression(db=db, impression_id=impression_id, message=message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(impression)}


@router.post("/{impression_id}/annuler")
def annuler_impression(impression_id: int, db: Session = Depends(get_db)):
    try:
        impression = ImpressionService.annuler_impression(db=db, impression_id=impression_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(impression)}
