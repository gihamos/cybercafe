from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.session_caisse import SessionCaisse
from models.paiement import Paiement, TypePaiement
from schemas.caisse_schema import CaisseOuvrir, CaisseCloturer
from services.caisse_service import CaisseService
from services.paiement_service import PaiementService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


def _serialize_paiement(p: Paiement) -> dict:
    return {
        "id": p.id,
        "montant": p.montant,
        "type_paiement": p.type_paiement,
        "statut": p.statut,
        "reference": p.reference,
        "user_id": p.user_id,
        "ticket_id": p.ticket_id,
        "date_paiement": p.date_paiement,
    }


router = APIRouter(
    prefix="/caisse",
    tags=["caisse"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize(session_caisse: SessionCaisse) -> dict:
    return {
        "id": session_caisse.id,
        "operateur_id": session_caisse.operateur_id,
        "montant_ouverture": session_caisse.montant_ouverture,
        "date_ouverture": session_caisse.date_ouverture,
        "montant_cloture_theorique": session_caisse.montant_cloture_theorique,
        "montant_cloture_reel": session_caisse.montant_cloture_reel,
        "ecart": session_caisse.ecart,
        "date_cloture": session_caisse.date_cloture,
        "est_ouverte": session_caisse.est_ouverte,
        "notes": session_caisse.notes,
    }


@router.post("/ouvrir", status_code=201)
def ouvrir(data: CaisseOuvrir, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        session_caisse = CaisseService.ouvrir(
            db=db, operateur_id=currentuser.get("id"), montant_ouverture=data.montant_ouverture
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(session_caisse)}


@router.get("/ouverte")
def get_ouverte(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    session_caisse = CaisseService.get_ouverte(db=db, operateur_id=currentuser.get("id"))
    return {"status_code": 200, "data": _serialize(session_caisse) if session_caisse else None}


@router.post("/{session_caisse_id}/cloturer")
def cloturer(session_caisse_id: int, data: CaisseCloturer, db: Session = Depends(get_db)):
    try:
        session_caisse = CaisseService.cloturer(
            db=db, session_caisse_id=session_caisse_id,
            montant_cloture_reel=data.montant_cloture_reel, notes=data.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(session_caisse)}


@router.get("/")
def lister(operateur_id: int | None = None, db: Session = Depends(get_db)):
    sessions = CaisseService.lister(db=db, operateur_id=operateur_id)
    return {"status_code": 200, "data": [_serialize(s) for s in sessions]}


@router.get("/{session_caisse_id}")
def get_one(session_caisse_id: int, db: Session = Depends(get_db)):
    try:
        session_caisse = CaisseService.get_by_id(db, session_caisse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(session_caisse)}


@router.get("/{session_caisse_id}/resume")
def resume(session_caisse_id: int, db: Session = Depends(get_db)):
    try:
        data = CaisseService.resume_session(db, session_caisse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": data}


@router.get("/{session_caisse_id}/transactions")
def transactions(session_caisse_id: int, db: Session = Depends(get_db)):
    try:
        result = CaisseService.lister_transactions(db, session_caisse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": [_serialize_paiement(p) for p in result]}


@router.post("/encaisser", status_code=201)
def encaisser(
    montant: float,
    type_paiement: TypePaiement,
    user_id: int | None = None,
    ticket_id: int | None = None,
    numero_telephone: str | None = None,
    crediter_solde: bool = False,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Encaissement direct au comptoir (recharge de solde, vente ponctuelle...), en
    dehors du flux d'achat d'article/abonnement — passe par la validation fournisseur
    pour carte/mobile money (voir PaiementService.encaisser_caisse). Si crediter_solde
    est vrai, le solde du client est crédité du montant dans la même transaction que
    l'enregistrement du paiement."""
    try:
        paiement = PaiementService.encaisser_caisse(
            db=db, montant=montant, type_paiement=type_paiement,
            operateur_id=currentuser.get("id"), user_id=user_id, ticket_id=ticket_id,
            metadata={"numero_telephone": numero_telephone} if numero_telephone else {},
            crediter_solde=crediter_solde,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize_paiement(paiement)}
