from fastapi import APIRouter, Depends, HTTPException, Request

from config.database import get_db
from sqlalchemy.orm import Session

from models.user import UserRole
from services.paiement_service import PaiementService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles
from utils.logger import logger


router = APIRouter(prefix="/paiement/en-ligne", tags=["paiements en ligne"])


@router.post(
    "/commande",
    status_code=201,
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)
def creer_commande(
    gateway: str,
    intent: str,
    user_id: int,
    montant: float | None = None,
    offre_id: int | None = None,
    devise: str = "EUR",
    db: Session = Depends(get_db)
):
    """Crée une commande de paiement en ligne (ex: PayPal) pour une recharge de solde
    ou l'achat d'une offre. Retourne une approval_url à ouvrir/partager avec le client
    (ex: lien envoyé depuis la caisse pour un paiement par carte/PayPal plutôt qu'en
    espèces). La confirmation effective arrive de façon asynchrone via le webhook."""
    try:
        result = PaiementService.creer_commande_en_ligne(
            db=db, gateway_nom=gateway, intent=intent, user_id=user_id,
            montant=montant, offre_id=offre_id, devise=devise
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": result}


@router.get(
    "/{paiement_id}/statut",
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)
def get_statut(paiement_id: int, db: Session = Depends(get_db)):
    try:
        paiement = PaiementService.get_by_id(db, paiement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": {"paiement_id": paiement.id, "statut": paiement.statut}}


@router.post("/webhook/{gateway}")
async def webhook(gateway: str, request: Request, db: Session = Depends(get_db)):
    """Endpoint public appelé directement par la passerelle de paiement (PayPal...) —
    pas d'authentification JWT possible ici, la sécurité vient de la vérification de
    signature du webhook (voir PaymentGateway.verifier_webhook)."""
    raw_body = await request.body()
    try:
        result = PaiementService.traiter_webhook_paiement(
            db=db, gateway_nom=gateway, headers=request.headers, raw_body=raw_body
        )
    except ValueError as e:
        logger.error(f"Webhook paiement rejeté ({gateway}): {e}")
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": result}
