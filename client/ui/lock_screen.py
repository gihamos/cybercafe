from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget
)

import platform_
from core.focus_guard import FocusGuard


class LockScreen(QWidget):
    """Écran kiosk plein écran affiché quand aucune session n'est active sur le poste."""

    login_submitted = Signal(str, str)   # username, password
    ticket_submitted = Signal(str)       # code

    def __init__(self, poste_nom: str = "", parent=None):
        super().__init__(parent)
        self._focus_guard = FocusGuard(self)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #f1f5f9; font-size: 15px; }
            QLineEdit {
                background-color: #1e293b; border: 1px solid #334155;
                border-radius: 6px; padding: 8px; color: #f1f5f9;
            }
            QPushButton {
                background-color: #2563eb; border-radius: 6px; padding: 10px;
                color: white; font-weight: bold; border: none;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #1e293b; padding: 8px 16px; color: #f1f5f9; }
            QTabBar::tab:selected { background: #2563eb; }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Cybercafé")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold;")
        layout.addWidget(title)

        self.poste_label = QLabel(poste_nom)
        self.poste_label.setAlignment(Qt.AlignCenter)
        self.poste_label.setStyleSheet("color: #94a3b8; margin-bottom: 20px;")
        layout.addWidget(self.poste_label)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #f87171; font-weight: bold;")
        layout.addWidget(self.error_label)

        tabs = QTabWidget()
        tabs.setFixedWidth(360)

        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        login_btn = QPushButton("Se connecter")
        login_btn.clicked.connect(self._submit_login)
        self.password_input.returnPressed.connect(self._submit_login)
        login_layout.addWidget(self.username_input)
        login_layout.addWidget(self.password_input)
        login_layout.addWidget(login_btn)
        tabs.addTab(login_tab, "Mon compte")

        ticket_tab = QWidget()
        ticket_layout = QVBoxLayout(ticket_tab)
        self.ticket_input = QLineEdit()
        self.ticket_input.setPlaceholderText("Code du ticket")
        ticket_btn = QPushButton("Valider le ticket")
        ticket_btn.clicked.connect(self._submit_ticket)
        self.ticket_input.returnPressed.connect(self._submit_ticket)
        ticket_layout.addWidget(self.ticket_input)
        ticket_layout.addWidget(ticket_btn)
        tabs.addTab(ticket_tab, "Ticket")

        centered = QHBoxLayout()
        centered.addStretch()
        centered.addWidget(tabs)
        centered.addStretch()
        layout.addLayout(centered)

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
