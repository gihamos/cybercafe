from services.router_gateway.base import RouterGateway, ConsommationReseau
from services.router_gateway.simulated_gateway import SimulatedGateway

# Pour ajouter un nouveau routeur/pare-feu (ex: OpenWrt, pfSense) : implémenter
# RouterGateway dans un nouveau fichier de ce dossier, puis l'enregistrer ci-dessous —
# rien d'autre à changer côté services/reseau_service.py ou routers.
_GATEWAYS = {
    "simulated": SimulatedGateway,
}


def _register_mikrotik():
    from services.router_gateway.mikrotik_gateway import MikrotikGateway
    _GATEWAYS["mikrotik"] = MikrotikGateway


_register_mikrotik()


def get_router_gateway(nom: str) -> RouterGateway:
    gateway_cls = _GATEWAYS.get(nom)
    if not gateway_cls:
        raise ValueError(f"Passerelle routeur inconnue : {nom}")
    return gateway_cls()


def liste_router_gateways() -> list[str]:
    return list(_GATEWAYS.keys())


__all__ = ["RouterGateway", "ConsommationReseau", "get_router_gateway", "liste_router_gateways"]
