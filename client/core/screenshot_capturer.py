from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication


def capturer_ecran() -> bytes | None:
    """Capture l'écran principal du poste en PNG. Retourne None si aucun écran n'est
    disponible (headless) — l'appelant doit simplement sauter le cycle d'envoi."""
    screen = QGuiApplication.primaryScreen()
    if not screen:
        return None

    pixmap = screen.grabWindow(0)
    if pixmap.isNull():
        return None

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()

    return bytes(data)
