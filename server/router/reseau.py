from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.session import Session as SessionModel
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/reseau", tags=["reseau"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin]))],
)


@router.get("/statut")
def statut_routeur():
    """Visibilité admin sur le contrôle réseau réel configuré (voir
    services/router_gateway/) : quelle passerelle est active, et un test de
    connectivité best-effort (ex: résolution MAC d'une IP factice pour vérifier que
    le routeur répond)."""
    from params import ROUTER_GATEWAY
    from services.router_gateway import get_router_gateway, liste_router_gateways

    joignable = None
    erreur = None
    try:
        gateway = get_router_gateway(ROUTER_GATEWAY)
        if ROUTER_GATEWAY != "simulated":
            gateway.resoudre_mac("0.0.0.0")  # requête légère, réponse vide attendue
        joignable = True
    except Exception as e:
        joignable = False
        erreur = str(e)

    return {"status_code": 200, "data": {
        "gateway_actif": ROUTER_GATEWAY,
        "gateways_disponibles": liste_router_gateways(),
        "joignable": joignable,
        "erreur": erreur,
    }}


@router.get("/sessions")
def sessions_controlees(db: Session = Depends(get_db)):
    """Sessions actives et leur état de contrôle réseau réel (identifiant, accès
    accordé ou non) — pour diagnostiquer un client qui aurait du réseau applicatif
    mais pas d'accès internet réel (ou l'inverse)."""
    sessions = db.query(SessionModel).filter(SessionModel.est_active == True).all()
    return {"status_code": 200, "data": [{
        "id": s.id,
        "poste_id": s.poste_id,
        "user_id": s.user_id,
        "ticket_id": s.ticket_id,
        "ip_client": s.ip_client or (s.poste.ip if s.poste else None),
        "mac_client": s.mac_client or (s.poste.mac_adresse if s.poste else None),
        "acces_reseau_actif": s.acces_reseau_actif,
    } for s in sessions]}


@router.post("/sites-bloques/resynchroniser")
def resynchroniser_sites_bloques(db: Session = Depends(get_db)):
    """Repousse manuellement la liste complète des sites bloqués vers le routeur —
    utile après un changement de passerelle ou un doute sur l'état du routeur."""
    from services.reseau_service import ReseauService
    try:
        ReseauService.synchroniser_sites_bloques(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": {"synchronise": True}}
