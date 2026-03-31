class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket, poste_id: int):
        await websocket.accept()
        self.active_connections[poste_id] = websocket

    async def send_to_poste(self, poste_id: int, message: str):
        ws = self.active_connections.get(poste_id)
        if ws:
            await ws.send_text(message)

manager = ConnectionManager()
