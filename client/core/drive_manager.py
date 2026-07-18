from PySide6.QtCore import QObject, QTimer

import platform_

CHECK_INTERVAL_MS = 2000


class DriveManager(QObject):
    """Applique en continu la politique de blocage de lecteurs reçue du serveur
    (message WS 'blocked_drives', voir server/services/lecteur_bloque_service.py)
    — même principe que ProcessGuard (core/process_guard.py) mais pour les
    périphériques de stockage plutôt que les processus. Tourne en continu,
    indépendamment de l'état de session : c'est une politique du poste."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocked_types: set[str] = set()
        self._verrouilles: set[str] = set()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)

    def set_blocked_types(self, types: list[str]):
        self._blocked_types = {t for t in types if t}

    def start(self):
        self._timer.start(CHECK_INTERVAL_MS)

    def stop(self):
        self._timer.stop()

    def _check(self):
        a_verrouiller = platform_.lecteurs_a_bloquer(self._blocked_types)

        for identifiant in a_verrouiller - self._verrouilles:
            platform_.verrouiller_lecteur(identifiant)

        for identifiant in self._verrouilles - a_verrouiller:
            platform_.deverrouiller_lecteur(identifiant)

        self._verrouilles = a_verrouiller
