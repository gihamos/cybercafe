import asyncio
from fastapi import WebSocket


class ConnectionManager:
    """Registre des connexions WebSocket des postes clients (un poste = une connexion active)."""

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Capture la boucle asyncio principale au démarrage de l'app (voir main.py)."""
        self.loop = loop

    async def connect(self, websocket: WebSocket, poste_id: int):
        await websocket.accept()
        self.active_connections[poste_id] = websocket

    def disconnect(self, poste_id: int):
        self.active_connections.pop(poste_id, None)

    def is_connected(self, poste_id: int) -> bool:
        return poste_id in self.active_connections

    async def send_to_poste(self, poste_id: int, message_type: str, data: dict | None = None) -> bool:
        ws = self.active_connections.get(poste_id)
        if not ws:
            return False
        await ws.send_json({"type": message_type, "data": data or {}})
        return True

    def send_to_poste_threadsafe(self, poste_id: int, message_type: str, data: dict | None = None):
        """À appeler depuis du code synchrone (endpoints REST exécutés en threadpool) pour
        pousser un message vers un poste connecté sans bloquer ni planter si la boucle
        principale n'est pas encore capturée ou si le poste n'est pas connecté."""
        if not self.loop:
            return
        asyncio.run_coroutine_threadsafe(
            self.send_to_poste(poste_id, message_type, data),
            self.loop
        )

    def broadcast_threadsafe(self, message_type: str, data: dict | None = None):
        if not self.loop:
            return
        for poste_id in list(self.active_connections.keys()):
            self.send_to_poste_threadsafe(poste_id, message_type, data)


manager = ConnectionManager()
