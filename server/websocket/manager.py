import asyncio
from fastapi import WebSocket


class ConnectionManager:
    """Registre des connexions WebSocket : postes clients (une connexion par poste_id)
    et panneau d'administration (plusieurs admins/opérateurs peuvent être connectés en
    même temps, donc une simple liste)."""

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}
        self.admin_connections: list[WebSocket] = []
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

    # -----------------------------------------------------
    # Panneau d'administration
    # -----------------------------------------------------
    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.append(websocket)

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)

    async def broadcast_to_admins(self, message_type: str, data: dict | None = None):
        payload = {"type": message_type, "data": data or {}}
        for ws in list(self.admin_connections):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect_admin(ws)

    def broadcast_to_admins_threadsafe(self, message_type: str, data: dict | None = None):
        """À appeler depuis du code synchrone (endpoints REST / services) pour notifier
        en temps réel tous les panneaux d'administration connectés."""
        if not self.loop:
            return
        asyncio.run_coroutine_threadsafe(
            self.broadcast_to_admins(message_type, data),
            self.loop
        )


manager = ConnectionManager()
