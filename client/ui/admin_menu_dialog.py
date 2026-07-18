from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QStackedWidget, QWidget
)

import platform_
from ui.theme import QSS


class AdminMenuDialog(QDialog):
    """Menu admin local du kiosk : authentification (compte Windows admin
    configuré, ou code de secours à usage unique généré à distance — voir
    server/services/Poste_service.py::generer_code_secours), puis choix d'une
    action (quitter le kiosk, réinitialiser la configuration réseau).

    Authentification entièrement locale — aucun appel réseau — pour fonctionner
    même sans connexion au serveur, sur le même principe que
    platform_.verify_admin_credentials (API Windows LogonUserW)."""

    ACTION_QUITTER_KIOSK = "quitter_kiosque"
    ACTION_RESET_RESEAU = "reinitialiser_reseau"

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Menu admin")
        self.setStyleSheet(QSS)
        self._config = config
        self._admin_username = (config.get("admin_windows_username") or "").strip()
        self.selected_action: str | None = None

        outer = QVBoxLayout(self)
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        self._build_auth_page()
        self._build_menu_page()

    def _build_auth_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        if not self._admin_username:
            layout.addWidget(QLabel(
                "Aucun compte admin n'est configuré sur ce poste.\n"
                "Configurez-en un dans les paramètres du client pour activer cette fonctionnalité."
            ))
            fermer = QPushButton("Fermer")
            fermer.clicked.connect(self.reject)
            layout.addWidget(fermer)
            self._stack.addWidget(page)
            return

        form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self._admin_username)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form.addRow("Identifiant Windows", self.username_input)
        form.addRow("Mot de passe (ou code de secours)", self.password_input)
        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        layout.addWidget(self.error_label)

        valider_btn = QPushButton("Continuer")
        valider_btn.setProperty("role", "primary")
        valider_btn.clicked.connect(self._authentifier)
        self.password_input.returnPressed.connect(self._authentifier)
        layout.addWidget(valider_btn)

        annuler_btn = QPushButton("Annuler")
        annuler_btn.clicked.connect(self.reject)
        layout.addWidget(annuler_btn)

        self._stack.addWidget(page)

    def _build_menu_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Authentification réussie. Choisissez une action :"))

        quitter_btn = QPushButton("Quitter le kiosk")
        quitter_btn.setProperty("role", "primary")
        quitter_btn.clicked.connect(lambda: self._choisir(self.ACTION_QUITTER_KIOSK))
        layout.addWidget(quitter_btn)

        reset_btn = QPushButton("Réinitialiser la configuration réseau")
        reset_btn.clicked.connect(lambda: self._choisir(self.ACTION_RESET_RESEAU))
        layout.addWidget(reset_btn)

        annuler_btn = QPushButton("Annuler")
        annuler_btn.clicked.connect(self.reject)
        layout.addWidget(annuler_btn)

        self._stack.addWidget(page)

    def _authentifier(self):
        username = self.username_input.text().strip()
        secret = self.password_input.text()
        if not username or not secret:
            self.error_label.setText("Identifiant et mot de passe requis")
            return

        if username.lower() == self._admin_username.lower() and platform_.verify_admin_credentials(username, secret):
            self._stack.setCurrentIndex(1)
            return

        if self._consommer_code_secours(secret):
            self._stack.setCurrentIndex(1)
            return

        self.error_label.setText("Identifiant/mot de passe ou code de secours incorrect")

    def _consommer_code_secours(self, code: str) -> bool:
        """Vérifie le code de secours mis en cache localement (voir main.py, message
        WS "code_secours") et l'invalide immédiatement après usage — à usage unique,
        y compris hors ligne, puisque l'invalidation est purement locale."""
        code_hash = self._config.get("code_secours_hash")
        expire_le = self._config.get("code_secours_expire_le")
        if not code_hash or not expire_le:
            return False
        try:
            if datetime.fromisoformat(expire_le) < datetime.utcnow():
                return False
        except ValueError:
            return False

        from pwdlib import PasswordHash
        try:
            valide = PasswordHash.recommended().verify(code, code_hash)
        except Exception:
            valide = False

        if valide:
            from config import save_config
            self._config["code_secours_hash"] = None
            self._config["code_secours_expire_le"] = None
            save_config(self._config)

        return valide

    def _choisir(self, action: str):
        self.selected_action = action
        self.accept()

    @staticmethod
    def demander_action(config: dict, parent=None) -> str | None:
        """Affiche le menu admin et renvoie l'action choisie (ou None si annulé
        ou authentification échouée)."""
        dialog = AdminMenuDialog(config, parent)
        dialog.exec()
        return dialog.selected_action
