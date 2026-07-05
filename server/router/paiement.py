from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.paiement import Paiement, TypePaiement
from schemas.paiement_schema import PaiementCreate
from services.paiement_service import PaiementService
from services.user_service import UserService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/paiement",
    tags=["paiements"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize(paiement: Paiement) -> dict:
    return {
        "id": paiement.id,
        "user_id": paiement.user_id,
        "ticket_id": paiement.ticket_id,
        "montant": paiement.montant,
        "devise": paiement.devise,
        "type_paiement": paiement.type_paiement,
        "statut": paiement.statut,
        "reference": paiement.reference,
        "date_paiement": paiement.date_paiement,
    }


@router.post("/", status_code=201)
def creer_paiement(data: PaiementCreate, db: Session = Depends(get_db)):
    try:
        paiement = PaiementService.creer_paiement(
            db=db,
            montant=data.montant,
            type_paiement=data.type_paiement,
            user_id=data.user_id,
            ticket_id=data.ticket_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(paiement)}


@router.get("/")
def rechercher_paiements(
    user_id: int | None = None,
    ticket_id: int | None = None,
    type_paiement: TypePaiement | None = None,
    statut: str | None = None,
    db: Session = Depends(get_db)
):
    paiements = PaiementService.rechercher_paiements(
        db=db, user_id=user_id, ticket_id=ticket_id, type_paiement=type_paiement, statut=statut
    )
    return {"status_code": 200, "data": [_serialize(p) for p in paiements]}


@router.get("/{paiement_id}")
def get_paiement(paiement_id: int, db: Session = Depends(get_db)):
    try:
        paiement = PaiementService.get_by_id(db, paiement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(paiement)}


@router.post("/{paiement_id}/rembourser")
def rembourser(paiement_id: int, db: Session = Depends(get_db)):
    try:
        paiement = PaiementService.rembourser(db=db, paiement_id=paiement_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(paiement)}


@router.post("/recharge/{user_iden}")
def recharger_solde(user_iden: str, montant: float, type_paiement: TypePaiement, db: Session = Depends(get_db)):
    try:
        nouveau_solde = UserService.ajouter_solde(db=db, user_iden=user_iden, montant=montant, type_paiement=type_paiement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": {"solde_euros": nouveau_solde}}
