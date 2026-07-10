from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.paiement import Paiement, TypePaiement
from models.achat_article import AchatArticle
from schemas.paiement_schema import PaiementCreate
from services.paiement_service import PaiementService
from services.user_service import UserService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(
    prefix="/paiement",
    tags=["paiements"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _resoudre_objet(db: Session, paiement: Paiement) -> dict | None:
    """Retrouve ce que ce paiement a réglé — un article, un forfait (abonnement direct
    ou via ticket), ou rien de particulier (ex: recharge de solde) — pour affichage
    côté panneau d'administration (voir PaiementsPage)."""
    if paiement.achat_id and paiement.achat and paiement.achat.offre:
        return {"type": "forfait", "nom": paiement.achat.offre.nom}

    if paiement.ticket_id and paiement.ticket:
        if paiement.ticket.offre:
            return {"type": "forfait", "nom": f"{paiement.ticket.offre.nom} (ticket {paiement.ticket.code})"}
        return {"type": "ticket", "nom": f"Ticket {paiement.ticket.code}"}

    achat_article = (
        db.query(AchatArticle)
        .filter(AchatArticle.paiement_id == paiement.id)
        .first()
    )
    if achat_article and achat_article.article:
        return {"type": "article", "nom": achat_article.article.nom}

    return None


def _serialize(paiement: Paiement, db: Session | None = None) -> dict:
    return {
        "id": paiement.id,
        "user_id": paiement.user_id,
        "user_nom": paiement.user.username if paiement.user else None,
        "ticket_id": paiement.ticket_id,
        "operateur_id": paiement.operateur_id,
        "operateur_nom": paiement.operateur.username if paiement.operateur else None,
        "montant": paiement.montant,
        "devise": paiement.devise,
        "type_paiement": paiement.type_paiement,
        "statut": paiement.statut,
        "reference": paiement.reference,
        "date_paiement": paiement.date_paiement,
        "objet": _resoudre_objet(db, paiement) if db is not None else None,
        "promotions": [
            {
                "id": pp.promotion.id,
                "nom": pp.promotion.nom,
                "code": pp.promotion.code,
                "montant_reduction": pp.montant_reduction,
            }
            for pp in paiement.promotions_appliquees
        ],
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

    return {"status_code": 201, "data": _serialize(paiement, db)}


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
    return {"status_code": 200, "data": [_serialize(p, db) for p in paiements]}


@router.get("/{paiement_id}")
def get_paiement(paiement_id: int, db: Session = Depends(get_db)):
    try:
        paiement = PaiementService.get_by_id(db, paiement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(paiement, db)}


@router.post("/{paiement_id}/rembourser")
def rembourser(paiement_id: int, db: Session = Depends(get_db)):
    try:
        paiement = PaiementService.rembourser(db=db, paiement_id=paiement_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(paiement, db)}


@router.post("/recharge/{user_iden}")
def recharger_solde(
    user_iden: str, montant: float, type_paiement: TypePaiement,
    currentuser=Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        nouveau_solde = UserService.ajouter_solde(
            db=db, user_iden=user_iden, montant=montant, type_paiement=type_paiement,
            operateur_id=currentuser.get("id")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": {"solde_euros": nouveau_solde}}
