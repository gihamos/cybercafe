from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PrintJobResult:
    """Représentation neutre (indépendante du système d'impression) d'un job envoyé
    à une imprimante, retournée par toutes les implémentations de PrintGateway."""

    job_id: str
    statut: str  # "en_file" | "en_cours" | "termine" | "erreur" | "inconnu"
    message: str | None = None


class PrintGateway(ABC):
    """Interface commune pour les systèmes d'impression (CUPS/Linux, spouleur
    Windows...). Toute nouvelle implémentation doit fournir ces méthodes pour être
    branchée sur services/impression_service.py sans rien changer côté appelant —
    voir print_gateway/__init__.py::get_print_gateway pour l'enregistrer."""

    nom: str

    @abstractmethod
    def imprimer(
        self,
        contenu: bytes,
        nom_fichier: str,
        copies: int = 1,
        recto_verso: bool = False,
        couleur: bool = False,
        imprimante: str | None = None,
    ) -> PrintJobResult:
        """Soumet un document à l'impression, retourne l'identifiant de job réel du
        système d'impression (pour un suivi ultérieur via get_statut)."""
        ...

    @abstractmethod
    def get_statut(self, job_id: str) -> PrintJobResult:
        """Interroge le système d'impression pour l'état réel d'un job déjà soumis."""
        ...

    @abstractmethod
    def annuler(self, job_id: str) -> None:
        ...

    @abstractmethod
    def lister_imprimantes(self) -> list[str]:
        """Imprimantes disponibles sur ce système — pour le choix dans les Paramètres."""
        ...
