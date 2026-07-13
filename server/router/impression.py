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


@router.get("/serveur/statut", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def statut_serveur_impression():
    """Visibilité admin sur le serveur d'impression réel configuré (voir
    services/print_gateway/) : passerelle active et imprimantes détectées."""
    from params import PRINT_GATEWAY
    from services.print_gateway import get_print_gateway, liste_print_gateways

    try:
        gateway = get_print_gateway(PRINT_GATEWAY)
        imprimantes = gateway.lister_imprimantes()
        erreur = None
    except Exception as e:
        imprimantes = []
        erreur = str(e)

    return {"status_code": 200, "data": {
        "gateway_actif": PRINT_GATEWAY,
        "gateways_disponibles": liste_print_gateways(),
        "imprimantes": imprimantes,
        "erreur": erreur,
    }}


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
        "paye": impression.paye,
        "document_disponible": bool((impression.details or {}).get("fichier_stocke_id")),
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


@router.get("/{impression_id}/document", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def telecharger_document(impression_id: int, db: Session = Depends(get_db)):
    """Document à imprimer, quand la demande vient du portail WiFi (le fichier est
    dans l'espace de stockage du client) — indispensable pour exécuter la demande."""
    from fastapi.responses import StreamingResponse
    from services.stockage_service import StockageService

    impression = db.query(Impression).get(impression_id)
    if not impression:
        raise HTTPException(status_code=404, detail="Impression introuvable")
    fichier_id = (impression.details or {}).get("fichier_stocke_id")
    if not fichier_id or not impression.user_id:
        raise HTTPException(status_code=404, detail="Document non disponible (demande hors portail)")
    try:
        fichier, flux = StockageService.telecharger_fichier(db=db, fichier_id=fichier_id, user_id=impression.user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StreamingResponse(
        flux, media_type=fichier.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fichier.nom_original}"'}
    )


@router.post("/{impression_id}/annuler")
def annuler_impression(impression_id: int, db: Session = Depends(get_db)):
    try:
        impression = ImpressionService.annuler_impression(db=db, impression_id=impression_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(impression)}
