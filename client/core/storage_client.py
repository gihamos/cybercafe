import requests

TIMEOUT = 20


class StorageError(Exception):
    pass


class StorageClient:
    """Client REST pour l'espace de stockage réseau, au nom de la session active sur ce
    poste (compte ou ticket, résolu côté serveur) — voir router/stockage_poste.py.
    Le stockage est un transfert de fichiers binaires : contrairement au reste du
    contrôle du poste (WebSocket), une requête HTTP classique est plus appropriée."""

    def __init__(self, server_url: str, poste_id: int, token: str):
        self._base = f"http://{server_url}/stockage/poste/{poste_id}"
        self._token = token

    def _params(self, **extra):
        params = {"token": self._token}
        params.update(extra)
        return params

    def get_quota(self) -> dict:
        r = requests.get(f"{self._base}/quota", params=self._params(), timeout=TIMEOUT)
        self._raise_for_status(r)
        return r.json()["data"]

    def lister_fichiers(self) -> list[dict]:
        r = requests.get(f"{self._base}/fichiers", params=self._params(), timeout=TIMEOUT)
        self._raise_for_status(r)
        return r.json()["data"]

    def upload(self, file_path: str, filename: str) -> dict:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{self._base}/upload", params=self._params(),
                files={"file": (filename, f)}, timeout=TIMEOUT
            )
        self._raise_for_status(r)
        return r.json()["data"]

    def download(self, fichier_id: int, dest_path: str) -> None:
        r = requests.get(
            f"{self._base}/fichiers/{fichier_id}/download", params=self._params(),
            timeout=TIMEOUT, stream=True
        )
        self._raise_for_status(r)
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    def supprimer(self, fichier_id: int) -> None:
        r = requests.delete(f"{self._base}/fichiers/{fichier_id}", params=self._params(), timeout=TIMEOUT)
        self._raise_for_status(r)

    @staticmethod
    def _raise_for_status(r):
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise StorageError(str(detail))
