from PySide6.QtCore import QObject, QTimer
import psutil

CHECK_INTERVAL_MS = 2000


class ProcessGuard(QObject):
    """Surveille les processus en cours sur le poste et termine ceux dont le nom
    correspond à la liste d'applications bloquées reçue du serveur (message WS
    'blocked_apps'). Tourne en continu (indépendamment de l'état de session) : le
    blocage d'applications est une politique du poste, pas seulement de la session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocked_names: set[str] = set()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)

    def set_blocked_apps(self, apps: list[str]):
        self._blocked_names = {a.lower() for a in apps if a}

    def start(self):
        self._timer.start(CHECK_INTERVAL_MS)

    def stop(self):
        self._timer.stop()

    def _check(self):
        if not self._blocked_names:
            return

        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if not name:
                    continue
                if name in self._blocked_names:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
