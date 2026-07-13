from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.session_caisse import SessionCaisse
from models.paiement import Paiement, TypePaiement
from models.vente_caisse import TypeLigneVente
from services.vente_caisse_service import VenteCaisseService
from schemas.caisse_schema import CaisseOuvrir, CaisseCloturer
from services.caisse_service import CaisseService
from services.paiement_service import PaiementService
from services.promotion_service import PromotionService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission, get_current_user


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
    dependencies=[
        Depends(auth_dependency),
        Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])),
        Depends(require_permission("caisse")),
    ]
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


@router.get("/verifier-promo")
def verifier_promo(
    code: str, montant: float, user_id: int | None = None, db: Session = Depends(get_db)
):
    """Aperçu d'un code promo avant encaissement — ne l'applique pas (n'incrémente pas
    son usage), sert uniquement à afficher sa référence et la réduction qu'il ferait
    avant que l'opérateur ne valide l'encaissement (voir CaissePage). Enregistrée avant
    les routes /{session_caisse_id}* pour éviter qu'elles n'avalent "verifier-promo"
    comme un id de session (même piège que /user/me/permissions, voir router/user.py)."""
    try:
        apercu = PromotionService.verifier_code(db=db, code=code, montant=montant, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": apercu}


# ---------------------------------------------------------
# CAISSE PRO : ventes groupées (tickets de caisse) + remboursements.
# Déclarées avant les routes /{session_caisse_id}* par précaution de collision.
# ---------------------------------------------------------

def _serialize_vente(vente) -> dict:
    return {
        "id": vente.id,
        "reference": vente.reference,
        "user_id": vente.user_id,
        "user_nom": vente.user.username if vente.user else None,
        "operateur_nom": vente.operateur.username if vente.operateur else None,
        "type_paiement": vente.type_paiement,
        "total": vente.total,
        "montant_rembourse": vente.montant_rembourse or 0,
        "statut": vente.statut,
        "date_vente": vente.date_vente,
        "lignes": [{
            "id": l.id,
            "type_ligne": l.type_ligne,
            "designation": l.designation,
            "prix_unitaire": l.prix_unitaire,
            "quantite": l.quantite,
            "quantite_remboursee": l.quantite_remboursee,
            "ticket_code": l.ticket.code if l.ticket else None,
            "remboursable": not (
                l.type_ligne == TypeLigneVente.ARTICLE and l.article and l.article.type_conservation == "frais"
            ) and (l.quantite - l.quantite_remboursee) > 0,
            "produit_frais": bool(l.type_ligne == TypeLigneVente.ARTICLE and l.article and l.article.type_conservation == "frais"),
        } for l in vente.lignes],
    }


@router.post("/vente", status_code=201)
def encaisser_vente(
    data: dict,
    type_paiement: TypePaiement = TypePaiement.ESPECES,
    user_id: int | None = None,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Encaissement caisse pro : ticket de caisse référencé (articles, forfaits,
    bons), client optionnel (vente au comptoir à un client de passage sinon).
    Corps : {"items": [{"type": "article"|"forfait"|"bon", "id"?, "montant"?, "quantite"}]}."""
    try:
        vente = VenteCaisseService.encaisser(
            db=db, operateur_id=currentuser.get("id"), items=data.get("items", []),
            type_paiement=type_paiement, user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": _serialize_vente(vente)}


@router.get("/ventes/{reference}")
def get_vente(reference: str, db: Session = Depends(get_db)):
    try:
        vente = VenteCaisseService.get_par_reference(db, reference)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status_code": 200, "data": _serialize_vente(vente)}


@router.get("/ventes/{reference}/ticket")
def ticket_de_caisse(reference: str, db: Session = Depends(get_db)):
    """Ticket de caisse imprimable (HTML) avec code-barres de la référence."""
    from fastapi.responses import HTMLResponse
    from services.recu_service import RecuService
    try:
        vente = VenteCaisseService.get_par_reference(db, reference)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return HTMLResponse(content=RecuService.generer_ticket_caisse_html(db, vente))


@router.post("/ventes/{reference}/rembourser")
def rembourser_vente(
    reference: str,
    data: dict,
    rembourser_sur_solde: bool = False,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remboursement total ou partiel d'un ticket de caisse.
    Corps : {"lignes": [{"ligne_id": int, "quantite": int}]}. Produits frais exclus,
    articles remis en stock, bons/codes non consommés désactivés."""
    try:
        result = VenteCaisseService.rembourser(
            db=db, reference=reference, lignes_demandees=data.get("lignes", []),
            operateur_id=currentuser.get("id"), rembourser_sur_solde=rembourser_sur_solde,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": result}


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


@router.post("/panier", status_code=201)
def encaisser_panier(
    user_id: int,
    data: dict,
    type_paiement: TypePaiement = TypePaiement.ESPECES,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Encaissement d'un panier (articles + forfaits groupés) au comptoir.
    Corps attendu : {"items": [{"type": "article"|"forfait", "id": int, "quantite": int}]}."""
    from services.portail_service import PortailService
    try:
        result = PortailService.commander_panier(
            db=db, user_id=user_id, items=data.get("items", []),
            utiliser_solde=False,
            type_paiement=type_paiement,
            operateur_id=currentuser.get("id"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": result}


@router.post("/encaisser", status_code=201)
def encaisser(
    montant: float,
    type_paiement: TypePaiement,
    user_id: int | None = None,
    ticket_id: int | None = None,
    numero_telephone: str | None = None,
    crediter_solde: bool = False,
    code_promo: str | None = None,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Encaissement direct au comptoir (recharge de solde, vente ponctuelle...), en
    dehors du flux d'achat d'article/abonnement — passe par la validation fournisseur
    pour carte/mobile money (voir PaiementService.encaisser_caisse). Si crediter_solde
    est vrai, le solde du client est crédité du montant dans la même transaction que
    l'enregistrement du paiement. code_promo est appliqué (et journalisé) avant tout,
    le fournisseur de paiement ne voit donc que le montant déjà remisé."""
    try:
        paiement = PaiementService.encaisser_caisse(
            db=db, montant=montant, type_paiement=type_paiement,
            operateur_id=currentuser.get("id"), user_id=user_id, ticket_id=ticket_id,
            metadata={"numero_telephone": numero_telephone} if numero_telephone else {},
            crediter_solde=crediter_solde,
            code_promo=code_promo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize_paiement(paiement)}
