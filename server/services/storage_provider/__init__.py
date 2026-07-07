from services.storage_provider.base import StorageProvider
from services.storage_provider.local_disk_provider import LocalDiskProvider
from params import STORAGE_LOCAL_PATH

# Pour ajouter un nouveau provider (ex: un autre cloud) : implémenter StorageProvider
# dans un nouveau fichier de ce dossier, l'enregistrer ci-dessous — rien d'autre à
# changer côté services/stockage_service.py ou routers.
_PROVIDERS = {
    "local": lambda: LocalDiskProvider(STORAGE_LOCAL_PATH),
}


def _register_s3():
    from services.storage_provider.s3_provider import S3Provider
    _PROVIDERS["s3"] = S3Provider


_register_s3()


def get_provider(nom: str) -> StorageProvider:
    factory = _PROVIDERS.get(nom)
    if not factory:
        raise ValueError(f"Fournisseur de stockage inconnu : {nom}")
    return factory()


def liste_providers() -> list[str]:
    return list(_PROVIDERS.keys())


__all__ = ["StorageProvider", "get_provider", "liste_providers"]
