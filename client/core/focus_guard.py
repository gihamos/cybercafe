from PySide6.QtCore import QObject, QTimer

CHECK_INTERVAL_MS = 300


class FocusGuard(QObject):
    """Filet de sécurité générique (Qt pur, marche sur les deux OS) : si la fenêtre
    surveillée arrive à perdre le premier plan (ex: un raccourci non bloqué par le
    durcissement plateforme laisse passer), on la reprend de force quasi
    instantanément. Complète le durcissement plateforme, ne le remplace pas."""

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self._window = window
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)

    def start(self):
        self._timer.start(CHECK_INTERVAL_MS)

    def stop(self):
        self._timer.stop()

    def _check(self):
        if self._window.isVisible() and not self._window.isActiveWindow():
            self._window.showFullScreen()
            self._window.raise_()
            self._window.activateWindow()
