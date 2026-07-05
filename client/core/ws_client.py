import asyncio
import json

from PySide6.QtCore import QThread, Signal
import websockets

from core.system_info import get_metrics

HEARTBEAT_INTERVAL_SECONDS = 15
RECONNECT_MAX_BACKOFF_SECONDS = 30


class WSClient(QThread):
    """Connexion WebSocket vers le serveur cybercafé, exécutée dans son propre thread
    avec sa propre boucle asyncio (pour ne jamais bloquer l'UI Qt). Toute communication
    vers l'extérieur passe par des Qt Signals, donc thread-safe côté UI."""

    message_received = Signal(str, dict)   # (type, data)
    connected = Signal()
    disconnected = Signal()

    def __init__(self, server_url: str, poste_id: int, token: str, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.poste_id = poste_id
        self.token = token

        self._loop: asyncio.AbstractEventLoop | None = None
        self._send_queue: asyncio.Queue | None = None
        self._stop_event: asyncio.Event | None = None

    # -----------------------------------------------------
    # API publique (appelée depuis le thread Qt principal)
    # -----------------------------------------------------
    def send(self, message_type: str, data: dict | None = None):
        if not self._loop or not self._send_queue:
            return
        asyncio.run_coroutine_threadsafe(
            self._send_queue.put((message_type, data or {})),
            self._loop
        )

    def stop(self):
        self._stop_requested = True
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)

    # -----------------------------------------------------
    # Boucle interne (thread dédié)
    # -----------------------------------------------------
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._loop.close()

    async def _main(self):
        self._send_queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        backoff = 1
        uri = f"ws://{self.server_url}/ws/poste/{self.poste_id}?token={self.token}"

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1
                    self.connected.emit()

                    consumer = asyncio.create_task(self._consume(ws))
                    producer = asyncio.create_task(self._produce(ws))
                    heartbeat = asyncio.create_task(self._heartbeat_loop(ws))
                    stopper = asyncio.create_task(self._stop_event.wait())

                    done, pending = await asyncio.wait(
                        [consumer, producer, heartbeat, stopper],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    for task in pending:
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass
            except (OSError, websockets.exceptions.WebSocketException):
                pass

            self.disconnected.emit()

            if self._stop_event.is_set():
                break

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, RECONNECT_MAX_BACKOFF_SECONDS)

    async def _consume(self, ws):
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            self.message_received.emit(msg.get("type", ""), msg.get("data") or {})

    async def _produce(self, ws):
        while True:
            message_type, data = await self._send_queue.get()
            await ws.send(json.dumps({"type": message_type, "data": data}))

    async def _heartbeat_loop(self, ws):
        while True:
            await ws.send(json.dumps({"type": "heartbeat", "data": get_metrics()}))
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
