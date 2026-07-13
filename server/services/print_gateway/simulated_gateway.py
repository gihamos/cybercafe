import uuid

from services.print_gateway.base import PrintGateway, PrintJobResult


class SimulatedGateway(PrintGateway):
    """Passerelle de démonstration/développement : aucune impression réelle, chaque
    job est immédiatement considéré terminé. Utile pour tester le flux Impression de
    bout en bout sans imprimante physique. À NE PAS utiliser en production."""

    nom = "simulated"

    def imprimer(
        self,
        contenu: bytes,
        nom_fichier: str,
        copies: int = 1,
        recto_verso: bool = False,
        couleur: bool = False,
        imprimante: str | None = None,
    ) -> PrintJobResult:
        return PrintJobResult(job_id=f"sim-{uuid.uuid4().hex[:10]}", statut="termine")

    def get_statut(self, job_id: str) -> PrintJobResult:
        return PrintJobResult(job_id=job_id, statut="termine")

    def annuler(self, job_id: str) -> None:
        pass

    def lister_imprimantes(self) -> list[str]:
        return ["Imprimante simulée"]
