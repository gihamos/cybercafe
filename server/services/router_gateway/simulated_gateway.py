from services.router_gateway.base import RouterGateway, ConsommationReseau
from utils.logger import logger


class SimulatedGateway(RouterGateway):
    """Passerelle de démonstration/développement : aucune action réseau réelle,
    seulement journalisée. Permet de développer/tester tout le flux de gestion de
    session sans routeur physique. À NE PAS utiliser en production."""

    nom = "simulated"

    def autoriser_acces(self, identifiant: str, download_kbps: int | None = None, upload_kbps: int | None = None) -> None:
        logger.info(f"[router:simulated] autoriser_acces({identifiant}, down={download_kbps}kbps, up={upload_kbps}kbps)")

    def revoquer_acces(self, identifiant: str) -> None:
        logger.info(f"[router:simulated] revoquer_acces({identifiant})")

    def definir_limite_debit(self, identifiant: str, download_kbps: int | None, upload_kbps: int | None) -> None:
        logger.info(f"[router:simulated] definir_limite_debit({identifiant}, down={download_kbps}kbps, up={upload_kbps}kbps)")

    def bloquer_domaines(self, domaines: list[str]) -> None:
        logger.info(f"[router:simulated] bloquer_domaines({domaines})")

    def resoudre_mac(self, ip: str) -> str | None:
        return None

    def get_consommation(self, identifiant: str) -> ConsommationReseau | None:
        return None
