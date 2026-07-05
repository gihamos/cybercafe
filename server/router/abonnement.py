from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.abonnement import Abonnement
from schemas.abonnement_schema import AbonnementSouscription
from services.abonnement_service import AbonnementService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(prefix="/abonnement", tags=["abonnements"], dependencies=[Depends(auth_dependency)])


def _serialize(abonnement: Abonnement) -> dict:
    return {
        "id": abonnement.id,
        "user_id": abonnement.user_id,
        "achat_id": abonnement.achat_id,
        "offre_id": abonnement.offre_id,
        "date_debut": abonnement.date_debut,
        "date_fin": abonnement.date_fin,
        "est_actif": abonnement.est_actif,
        "est_suspendu": abonnement.est_suspendu,
        "minutes_par_jour": abonnement.minutes_par_jour,
        "minutes_restantes_aujourdhui": abonnement.minutes_restantes_aujourdhui,
        "data_totale_mo": abonnement.data_totale_mo,
        "data_restante_mo": abonnement.data_restante_mo,
        "illimite": abonnement.illimite,
    }


@router.post("/souscrire", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def souscrire(data: AbonnementSouscription, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        abonnement = AbonnementService.souscrire(
            db=db,
            user_id=data.user_id,
            offre_id=data.offre_id,
            operateur_id=currentuser.get("id"),
            type_paiement=data.type_paiement,
            utiliser_solde=data.utiliser_solde
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(abonnement)}


@router.get("/{abonnement_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_abonnement(abonnement_id: int, db: Session = Depends(get_db)):
    try:
        abonnement = AbonnementService.get_by_id(db, abonnement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(abonnement)}


@router.get("/user/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_abonnements_user(user_id: int, db: Session = Depends(get_db)):
    abonnements = AbonnementService.get_by_user(db, user_id)
    return {"status_code": 200, "data": [_serialize(a) for a in abonnements]}


@router.patch("/{abonnement_id}/suspendre", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def suspendre(abonnement_id: int, db: Session = Depends(get_db)):
    try:
        abonnement = AbonnementService.set_suspendu(db=db, abonnement_id=abonnement_id, suspendu=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(abonnement)}


@router.patch("/{abonnement_id}/reactiver", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def reactiver(abonnement_id: int, db: Session = Depends(get_db)):
    try:
        abonnement = AbonnementService.set_suspendu(db=db, abonnement_id=abonnement_id, suspendu=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(abonnement)}


@router.delete("/{abonnement_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def terminer(abonnement_id: int, db: Session = Depends(get_db)):
    try:
        abonnement = AbonnementService.terminer(db=db, abonnement_id=abonnement_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(abonnement)}
