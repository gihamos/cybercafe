import sys

from PySide6.QtWidgets import (
    QApplication, QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox
)

from config import load_config, save_config, is_configured
from core.ws_client import WSClient
from core.process_guard import ProcessGuard
from core.storage_client import StorageClient
from ui.lock_screen import LockScreen
from ui.session_overlay import SessionOverlay
from ui.article_shop import ArticleShopDialog
from ui.print_dialog import PrintDialog
from ui.chat_panel import ChatDialog
from ui.storage_manager import StorageDialog
from ui.theme import QSS


class SetupDialog(QDialog):
    """Assistant de première configuration : saisie unique de l'adresse serveur,
    de l'ID du poste et de son token (fournis par l'admin à la création du poste)."""

    def __init__(self, config: dict):
        super().__init__()
        self.setWindowTitle("Configuration du poste")
        self.setStyleSheet(QSS)
        self.config = config

        layout = QFormLayout(self)

        self.server_input = QLineEdit(config.get("server_url") or "")
        self.server_input.setPlaceholderText("ex: 192.168.1.10:8000")
        self.poste_id_input = QLineEdit(str(config.get("poste_id") or ""))
        self.token_input = QLineEdit(config.get("token") or "")

        layout.addRow("Adresse du serveur", self.server_input)
        layout.addRow("ID du poste", self.poste_id_input)
        layout.addRow("Token du poste", self.token_input)

        save_btn = QPushButton("Enregistrer et démarrer")
        save_btn.setProperty("role", "primary")
        save_btn.clicked.connect(self._save)
        layout.addRow(save_btn)

    def _save(self):
        server_url = self.server_input.text().strip()
        poste_id_text = self.poste_id_input.text().strip()
        token = self.token_input.text().strip()

        if not server_url or not poste_id_text or not token:
            QMessageBox.warning(self, "Champs manquants", "Tous les champs sont requis.")
            return
        if not poste_id_text.isdigit():
            QMessageBox.warning(self, "ID invalide", "L'ID du poste doit être un nombre.")
            return

        self.config["server_url"] = server_url
        self.config["poste_id"] = int(poste_id_text)
        self.config["token"] = token
        save_config(self.config)
        self.accept()


class PosteClientApp:
    def __init__(self, config: dict):
        self.config = config
        self.ws = WSClient(config["server_url"], config["poste_id"], config["token"])
        self.lock_screen = LockScreen(poste_nom=f"Poste #{config['poste_id']}")
        self.session_overlay = SessionOverlay()
        self.article_shop = ArticleShopDialog()
        self.print_dialog = PrintDialog()
        self.chat_dialog = ChatDialog()
        self.storage_dialog = StorageDialog()
        self.process_guard = ProcessGuard()
        self.current_session = None
        self._pending_pay_connect_id = None

        self.ws.message_received.connect(self._on_message)
        self.ws.disconnected.connect(self._on_disconnected)

        self.lock_screen.login_submitted.connect(
            lambda u, p: self.ws.send("session_request", {"username": u, "password": p})
        )
        self.lock_screen.ticket_submitted.connect(
            lambda code: self.ws.send("session_request", {"code": code})
        )
        self.lock_screen.chat_clicked.connect(self.chat_dialog.show)
        self.lock_screen.pay_connect_tab.tarifs_requested.connect(
            lambda: self.ws.send("pay_connect_tarifs_request", {})
        )
        self.lock_screen.pay_connect_tab.solde_submitted.connect(
            lambda u, p, m: self.ws.send("pay_connect_solde", {"username": u, "password": p, "minutes": m})
        )
        self.lock_screen.pay_connect_tab.especes_submitted.connect(
            lambda m: self.ws.send("pay_connect_request", {"minutes": m})
        )
        self.lock_screen.pay_connect_tab.cancel_requested.connect(
            lambda request_id: self.ws.send("pay_connect_cancel", {"id": request_id})
        )

        self.session_overlay.end_session_clicked.connect(
            lambda: self.ws.send("session_end_request", {})
        )
        self.session_overlay.buy_article_clicked.connect(self.article_shop.show)
        self.session_overlay.print_clicked.connect(self.print_dialog.show)
        self.session_overlay.chat_clicked.connect(self.chat_dialog.show)
        self.session_overlay.storage_clicked.connect(self._open_storage)

        self.article_shop.refresh_requested.connect(
            lambda: self.ws.send("list_articles_request", {})
        )
        self.article_shop.buy_requested.connect(
            lambda article_id: self.ws.send("buy_article", {"article_id": article_id})
        )
        self.print_dialog.billing_requested.connect(
            lambda data: self.ws.send("print_billing", data)
        )
        self.chat_dialog.message_sent.connect(
            lambda text: self.ws.send("chat_message", {"message": text})
        )

    def start(self):
        self.lock_screen.show_kiosk()
        self.process_guard.start()
        self.ws.start()

    def shutdown(self):
        self.process_guard.stop()
        self.ws.stop()
        self.ws.wait(2000)

    def _on_disconnected(self):
        self.lock_screen.show_error("Connexion au serveur perdue, nouvelle tentative...")
        self.session_overlay.hide()
        self.lock_screen.show_kiosk()

    def _open_storage(self):
        client = StorageClient(self.config["server_url"], self.config["poste_id"], self.config["token"])
        self.storage_dialog.set_client(client)
        self.storage_dialog.show()

    def _on_message(self, msg_type: str, data: dict):
        if msg_type == "paired":
            if data.get("session"):
                self._enter_session(data["session"])
            else:
                self.lock_screen.reset()
                self.lock_screen.show_kiosk()

        elif msg_type == "session_started":
            self._enter_session(data)

        elif msg_type == "session_error":
            self.lock_screen.show_error(data.get("message", "Erreur"))

        elif msg_type in ("session_ended", "lock"):
            self._exit_session()

        elif msg_type == "articles_list":
            self.article_shop.set_articles(data.get("articles", []))

        elif msg_type == "purchase_result":
            self.article_shop.show_purchase_result(data.get("success", False), data.get("message", ""))

        elif msg_type == "print_result":
            self.print_dialog.show_billing_result(data.get("success", False), data.get("message", ""))

        elif msg_type == "blocked_apps":
            self.process_guard.set_blocked_apps(data.get("apps", []))

        elif msg_type == "chat_history":
            self.chat_dialog.set_history(data.get("messages", []))

        elif msg_type == "chat_message":
            self.chat_dialog.add_message(data)

        elif msg_type == "pay_connect_tarifs":
            self.lock_screen.pay_connect_tab.set_tarifs(data.get("tarifs", []))

        elif msg_type == "pay_connect_pending":
            self._pending_pay_connect_id = data.get("id")
            self.lock_screen.pay_connect_tab.show_pending(data.get("id"), data.get("montant", 0))

        elif msg_type == "pay_connect_error":
            self.lock_screen.pay_connect_tab.show_error(data.get("message", "Erreur"))

        elif msg_type == "pay_connect_refused":
            self._pending_pay_connect_id = None
            self.lock_screen.pay_connect_tab.show_refused()

        elif msg_type == "pay_connect_cancelled":
            self._pending_pay_connect_id = None

        elif msg_type == "message":
            QMessageBox.information(None, "Message", data.get("text", ""))

    def _enter_session(self, session_data: dict):
        self.current_session = session_data
        self.session_overlay.set_session(
            session_data.get("limite_minutes"),
            session_data.get("consommation_minutes", 0),
            session_data.get("limite_data_mo"),
            session_data.get("consommation_data_mo", 0),
        )
        self.lock_screen.hide_kiosk()
        self.session_overlay.show_at_top_right()

    def _exit_session(self):
        self.current_session = None
        self.storage_dialog.hide()
        self.session_overlay.hide()
        self.lock_screen.reset()
        self.lock_screen.show_kiosk()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = load_config()
    if not is_configured(config):
        dialog = SetupDialog(config)
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        config = load_config()

    poste_app = PosteClientApp(config)
    app.aboutToQuit.connect(poste_app.shutdown)
    poste_app.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
