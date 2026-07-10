import io

import requests

TIMEOUT = 20


class SurveillanceError(Exception):
    pass


class SurveillanceClient:
    """Client REST pour l'envoi périodique de captures d'écran et d'entrées
    d'historique de navigation, au nom du poste (authentification par token, voir
    router/surveillance_poste.py) — même choix qu'un transfert HTTP classique plutôt
    que le WebSocket pour les données volumineuses (voir storage_client.py)."""

    def __init__(self, server_url: str, poste_id: int, token: str):
        self._base = f"http://{server_url}/surveillance-poste/{poste_id}"
        self._token = token

    def _params(self, **extra):
        params = {"token": self._token}
        params.update(extra)
        return params

    def get_config(self) -> dict:
        r = requests.get(f"{self._base}/config", params=self._params(), timeout=TIMEOUT)
        self._raise_for_status(r)
        return r.json()["data"]

    def envoyer_capture(self, png_bytes: bytes) -> dict:
        r = requests.post(
            f"{self._base}/capture", params=self._params(),
            files={"file": ("capture.png", io.BytesIO(png_bytes), "image/png")}, timeout=TIMEOUT
        )
        self._raise_for_status(r)
        return r.json()["data"]

    def envoyer_historique(self, entrees: list[dict]) -> dict:
        if not entrees:
            return {"inserees": 0}
        r = requests.post(
            f"{self._base}/historique", params=self._params(), json=entrees, timeout=TIMEOUT
        )
        self._raise_for_status(r)
        return r.json()["data"]

    @staticmethod
    def _raise_for_status(r):
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise SurveillanceError(str(detail))
