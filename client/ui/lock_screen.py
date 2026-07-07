from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QFrame
)

import platform_
from core.focus_guard import FocusGuard
from ui.theme import QSS
from ui.pay_connect_tab import PayConnectTab


class LockScreen(QWidget):
    """Écran kiosk plein écran affiché quand aucune session n'est active sur le poste."""

    login_submitted = Signal(str, str)   # username, password
    ticket_submitted = Signal(str)       # code
    chat_clicked = Signal()

    def __init__(self, poste_nom: str = "", parent=None):
        super().__init__(parent)
        self._focus_guard = FocusGuard(self)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setStyleSheet(QSS)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Cybercafé")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("role", "title")
        layout.addWidget(title)

        self.poste_label = QLabel(poste_nom)
        self.poste_label.setAlignment(Qt.AlignCenter)
        self.poste_label.setProperty("role", "subtitle")
        self.poste_label.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(self.poste_label)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setProperty("role", "error")
        layout.addWidget(self.error_label)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)

        tabs = QTabWidget()
        tabs.setFixedWidth(380)

        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        login_btn = QPushButton("Se connecter")
        login_btn.setProperty("role", "primary")
        login_btn.clicked.connect(self._submit_login)
        self.password_input.returnPressed.connect(self._submit_login)
        login_layout.addWidget(self.username_input)
        login_layout.addWidget(self.password_input)
        login_layout.addWidget(login_btn)
        login_layout.addStretch()
        tabs.addTab(login_tab, "Mon compte")

        ticket_tab = QWidget()
        ticket_layout = QVBoxLayout(ticket_tab)
        self.ticket_input = QLineEdit()
        self.ticket_input.setPlaceholderText("Code du ticket")
        ticket_btn = QPushButton("Valider le ticket")
        ticket_btn.setProperty("role", "primary")
        ticket_btn.clicked.connect(self._submit_ticket)
        self.ticket_input.returnPressed.connect(self._submit_ticket)
        ticket_layout.addWidget(self.ticket_input)
        ticket_layout.addWidget(ticket_btn)
        ticket_layout.addStretch()
        tabs.addTab(ticket_tab, "Ticket")

        self.pay_connect_tab = PayConnectTab()
        tabs.addTab(self.pay_connect_tab, "Connexion rapide")

        card_layout.addWidget(tabs)

        centered = QHBoxLayout()
        centered.addStretch()
        centered.addWidget(card)
        centered.addStretch()
        layout.addLayout(centered)

        chat_row = QHBoxLayout()
        chat_row.addStretch()
        chat_btn = QPushButton("💬 Besoin d'aide ? Discuter avec l'opérateur")
        chat_btn.setProperty("role", "ghost")
        chat_btn.clicked.connect(self.chat_clicked.emit)
        chat_row.addWidget(chat_btn)
        chat_row.addStretch()
        layout.addLayout(chat_row)

        self._tabs = tabs

    def _submit_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.show_error("Veuillez saisir votre identifiant et mot de passe")
            return
        self.set_busy(True)
        self.login_submitted.emit(username, password)

    def _submit_ticket(self):
        code = self.ticket_input.text().strip()
        if not code:
            self.show_error("Veuillez saisir un code ticket")
            return
        self.set_busy(True)
        self.ticket_submitted.emit(code)

    def show_error(self, message: str):
        self.error_label.setText(message)
        self.set_busy(False)

    def set_busy(self, busy: bool):
        self.username_input.setEnabled(not busy)
        self.password_input.setEnabled(not busy)
        self.ticket_input.setEnabled(not busy)

    def reset(self):
        self.password_input.clear()
        self.ticket_input.clear()
        self.error_label.setText("")
        self.set_busy(False)
        self.pay_connect_tab.reset()

    def show_kiosk(self):
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        platform_.install_hardening(int(self.winId()))
        self._focus_guard.start()

    def hide_kiosk(self):
        self._focus_guard.stop()
        platform_.uninstall_hardening()
        self.hide()
