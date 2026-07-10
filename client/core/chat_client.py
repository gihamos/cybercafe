import requests

TIMEOUT = 20


class ChatError(Exception):
    pass


class ChatClient:
    """Client REST pour l'envoi/téléchargement de pièces jointes du chat, au nom du
    poste (authentification par token, voir router/chat_poste.py) — les messages
    texte, eux, continuent de transiter par le WebSocket (WSClient), un envoi de
    fichier binaire est plus adapté à une requête HTTP classique (même choix que
    pour l'espace de stockage réseau, voir storage_client.py)."""

    def __init__(self, server_url: str, poste_id: int, token: str):
        self._base = f"http://{server_url}/chat-poste/{poste_id}"
        self._token = token

    def _params(self, **extra):
        params = {"token": self._token}
        params.update(extra)
        return params

    def send_file(self, message: str, file_path: str, filename: str) -> dict:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{self._base}/message-fichier", params=self._params(),
                data={"message": message}, files={"file": (filename, f)}, timeout=TIMEOUT
            )
        self._raise_for_status(r)
        return r.json()["data"]

    def download_piece_jointe(self, message_id: int, dest_path: str) -> None:
        r = requests.get(
            f"{self._base}/message/{message_id}/piece-jointe", params=self._params(),
            timeout=TIMEOUT, stream=True
        )
        self._raise_for_status(r)
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    @staticmethod
    def _raise_for_status(r):
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ChatError(str(detail))
