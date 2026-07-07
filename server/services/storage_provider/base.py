from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageProvider(ABC):
    """Interface commune pour les fournisseurs de stockage de fichiers (disque local,
    S3/MinIO...). Toute nouvelle implémentation doit fournir ces méthodes pour être
    branchée sur services/stockage_service.py sans rien changer côté appelant — voir
    storage_provider/__init__.py::get_provider pour l'enregistrer."""

    nom: str

    @abstractmethod
    def upload(self, cle: str, fileobj: BinaryIO) -> int:
        """Écrit le contenu de fileobj sous la clé donnée, retourne la taille en octets."""
        ...

    @abstractmethod
    def download(self, cle: str) -> BinaryIO:
        """Retourne un flux binaire positionné au début du fichier."""
        ...

    @abstractmethod
    def delete(self, cle: str) -> None:
        """Supprime le fichier. Ne doit pas lever d'erreur si la clé n'existe déjà plus."""
        ...

    @abstractmethod
    def exists(self, cle: str) -> bool:
        ...
