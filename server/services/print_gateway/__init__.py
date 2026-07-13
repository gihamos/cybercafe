from services.print_gateway.base import PrintGateway, PrintJobResult
from services.print_gateway.simulated_gateway import SimulatedGateway

# Pour ajouter un nouveau système d'impression : implémenter PrintGateway dans un
# nouveau fichier de ce dossier, puis l'enregistrer ci-dessous — rien d'autre à
# changer côté services/impression_service.py ou routers. CUPS et Windows sont
# enregistrés paresseusement (imports conditionnels) pour ne jamais faire planter le
# démarrage du serveur sur une plateforme où l'un des deux n'est pas disponible.
_GATEWAYS = {
    "simulated": SimulatedGateway,
}


def _register_cups():
    from services.print_gateway.cups_gateway import CupsGateway
    _GATEWAYS["cups"] = CupsGateway


def _register_windows():
    from services.print_gateway.windows_gateway import WindowsGateway
    _GATEWAYS["windows"] = WindowsGateway


_register_cups()
_register_windows()


def get_print_gateway(nom: str) -> PrintGateway:
    gateway_cls = _GATEWAYS.get(nom)
    if not gateway_cls:
        raise ValueError(f"Système d'impression inconnu : {nom}")
    return gateway_cls()


def liste_print_gateways() -> list[str]:
    return list(_GATEWAYS.keys())


__all__ = ["PrintGateway", "PrintJobResult", "get_print_gateway", "liste_print_gateways"]
