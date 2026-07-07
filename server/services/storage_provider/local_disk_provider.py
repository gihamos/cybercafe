import shutil
from pathlib import Path
from typing import BinaryIO

from services.storage_provider.base import StorageProvider


class LocalDiskProvider(StorageProvider):
    """Stockage sur le disque local du serveur. Provider par défaut, toujours
    disponible (aucune dépendance/configuration externe requise)."""

    nom = "local"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, cle: str) -> Path:
        # cle est générée par stockage_service (uuid), mais on se protège quand même
        # d'une éventuelle traversée de répertoire ("../..") avant de toucher au disque.
        path = (self.root / cle).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise ValueError("Clé de stockage invalide")
        return path

    def upload(self, cle: str, fileobj: BinaryIO) -> int:
        path = self._resolve(cle)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            shutil.copyfileobj(fileobj, f)
        return path.stat().st_size

    def download(self, cle: str) -> BinaryIO:
        path = self._resolve(cle)
        return open(path, "rb")

    def delete(self, cle: str) -> None:
        path = self._resolve(cle)
        path.unlink(missing_ok=True)

    def exists(self, cle: str) -> bool:
        return self._resolve(cle).exists()
