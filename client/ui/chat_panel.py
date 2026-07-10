from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QWidget, QFrame, QSizePolicy, QFileDialog
)

from ui.theme import QSS, ACCENT, SURFACE_ALT


def _human_size(octets: int) -> str:
    if octets < 1024:
        return f"{octets} o"
    if octets < 1024 * 1024:
        return f"{octets / 1024:.1f} Ko"
    return f"{octets / (1024 * 1024):.1f} Mo"


class _Bubble(QFrame):
    download_clicked = Signal(int, str)

    def __init__(self, msg: dict, mine: bool, heure: str):
        super().__init__()
        self.setObjectName("card")
        self.setMaximumWidth(320)
        self.setStyleSheet(
            f"QFrame#card {{ background-color: {ACCENT if mine else SURFACE_ALT}; "
            f"border: none; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        message = msg.get("message", "")
        if message:
            text = QLabel(message)
            text.setWordWrap(True)
            text.setStyleSheet("color: white; background: transparent;" if mine else "background: transparent;")
            layout.addWidget(text)

        piece_jointe_nom = msg.get("piece_jointe_nom")
        if piece_jointe_nom:
            taille = _human_size(msg.get("piece_jointe_taille_octets") or 0)
            attach_btn = QPushButton(f"\U0001F4CE {piece_jointe_nom}  ({taille})")
            attach_btn.setCursor(Qt.PointingHandCursor)
            attach_btn.setStyleSheet(
                ("color: white; background: rgba(255,255,255,0.15);" if mine
                 else "color: inherit; background: rgba(0,0,0,0.06);")
                + " border: none; border-radius: 6px; padding: 6px 8px; text-align: left;"
            )
            attach_btn.clicked.connect(
                lambda: self.download_clicked.emit(msg.get("id"), piece_jointe_nom)
            )
            layout.addWidget(attach_btn)

        time_label = QLabel(heure)
        time_label.setStyleSheet(
            ("color: rgba(255,255,255,0.75);" if mine else "color: #8b93a7;") + " background: transparent; font-size: 11px;"
        )
        time_label.setAlignment(Qt.AlignRight)
        layout.addWidget(time_label)


class ChatDialog(QDialog):
    """Fil de discussion en direct avec l'opérateur, rattaché au poste (persistant :
    l'historique est renvoyé par le serveur à chaque (re)connexion du poste)."""

    message_sent = Signal(str)
    file_attach_requested = Signal(str, str)  # file_path, message accompagnant
    download_requested = Signal(int, str)  # message_id, nom de fichier suggéré

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Discuter avec l'opérateur")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(QSS)
        self.resize(420, 560)

        layout = QVBoxLayout(self)

        title = QLabel("Discuter avec l'opérateur")
        title.setProperty("role", "title")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._messages_layout = QVBoxLayout(self._container)
        self._messages_layout.addStretch()
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Écrire un message...")
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input, 1)

        attach_btn = QPushButton("\U0001F4CE")
        attach_btn.setToolTip("Joindre un fichier")
        attach_btn.clicked.connect(self._attach)
        input_row.addWidget(attach_btn)

        send_btn = QPushButton("Envoyer")
        send_btn.setProperty("role", "primary")
        send_btn.clicked.connect(self._send)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

    def _send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.message_sent.emit(text)

    def _attach(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier à envoyer")
        if not file_path:
            return
        text = self.input.text().strip()
        self.input.clear()
        self.file_attach_requested.emit(file_path, text)

    def _format_heure(self, iso_date: str) -> str:
        try:
            return datetime.fromisoformat(iso_date).strftime("%H:%M")
        except (ValueError, TypeError):
            return ""

    def set_history(self, messages: list[dict]):
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for msg in messages:
            self._insert_bubble(msg)
        self._scroll_to_bottom()

    def add_message(self, msg: dict):
        self._insert_bubble(msg)
        self._scroll_to_bottom()

    def _insert_bubble(self, msg: dict):
        mine = msg.get("expediteur") == "client"
        bubble = _Bubble(msg, mine, self._format_heure(msg.get("date_envoi", "")))
        bubble.download_clicked.connect(self.download_requested)
        row = QHBoxLayout()
        if mine:
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        wrapper = QWidget()
        wrapper.setLayout(row)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, wrapper)

    def _scroll_to_bottom(self):
        QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))
