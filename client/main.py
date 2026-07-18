import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication, QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox, QFileDialog
)

from config import load_config, save_config, is_configured
from core.ws_client import WSClient
from core.process_guard import ProcessGuard
from core.drive_manager import DriveManager
from core.storage_client import StorageClient
from core.chat_client import ChatClient, ChatError
from core.surveillance_client import SurveillanceClient, SurveillanceError
from core.screenshot_capturer import capturer_ecran
from core.browser_history_reader import lire_historique_recent
from core import hosts_manager
from core import system_commands
from ui.lock_screen import LockScreen
from ui.ticket_picker import TicketPickerDialog
from ui.session_overlay import SessionOverlay
from ui.article_shop import ArticleShopDialog
from ui.receipts_dialog import ReceiptsDialog
from ui.print_dialog import PrintDialog
from ui.chat_panel import ChatDialog
from ui.storage_manager import StorageDialog
from ui.theme import QSS

logger = logging.getLogger("cybercafe.client")


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
        self.admin_username_input = QLineEdit(config.get("admin_windows_username") or "")
        self.admin_username_input.setPlaceholderText("ex: admin-local (optionnel)")

        layout.addRow("Adresse du serveur", self.server_input)
        layout.addRow("ID du poste", self.poste_id_input)
        layout.addRow("Token du poste", self.token_input)
        layout.addRow("Compte Windows admin (désactivation kiosk)", self.admin_username_input)

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
        self.config["admin_windows_username"] = self.admin_username_input.text().strip()
        save_config(self.config)
        self.accept()


class PosteClientApp:
    def __init__(self, config: dict):
        self.config = config
        self.ws = WSClient(config["server_url"], config["poste_id"], config["token"])
        self.lock_screen = LockScreen(poste_nom=f"Poste #{config['poste_id']}")
        self.session_overlay = SessionOverlay()
        self.article_shop = ArticleShopDialog()
        self.receipts_dialog = ReceiptsDialog()
        self.print_dialog = PrintDialog()
        self.chat_dialog = ChatDialog()
        self.storage_dialog = StorageDialog()
        self.process_guard = ProcessGuard()
        self.drive_manager = DriveManager()
        self.current_session = None
        self._pending_pay_connect_id = None
        self._pending_creds: tuple[str, str] | None = None

        # Surveillance (captures d'écran + historique navigateur), voir _start_surveillance —
        # actifs uniquement pendant une session, jamais sur l'écran de verrouillage.
        self.surveillance_client: SurveillanceClient | None = None
        self._capture_timer = QTimer()
        self._capture_timer.timeout.connect(self._on_capture_tick)
        self._historique_timer = QTimer()
        self._historique_timer.timeout.connect(self._on_historique_tick)
        self._historique_watermark = datetime.now(timezone.utc)

        self.ws.message_received.connect(self._on_message)
        self.ws.disconnected.connect(self._on_disconnected)

        self._charger_charte()

        self.lock_screen.login_submitted.connect(self._on_login_submitted)
        self.lock_screen.ticket_submitted.connect(
            lambda code: self.ws.send("session_request", {
                "code": code, "charte_acceptee": self.lock_screen.charte_acceptee(),
            })
        )
        self.lock_screen.chat_clicked.connect(self.chat_dialog.show)
        self.lock_screen.disable_kiosk_requested.connect(self._on_disable_kiosk_requested)
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
        self.session_overlay.change_ticket_clicked.connect(
            lambda: self.ws.send("mes_tickets_request", {})
        )
        self.session_overlay.buy_article_clicked.connect(self.article_shop.show)
        self.session_overlay.print_clicked.connect(self.print_dialog.show)
        self.session_overlay.chat_clicked.connect(self.chat_dialog.show)
        self.session_overlay.storage_clicked.connect(self._open_storage)
        self.session_overlay.receipts_clicked.connect(self.receipts_dialog.show)

        self.receipts_dialog.refresh_requested.connect(self._rafraichir_recus)
        self.receipts_dialog.receipt_requested.connect(self._telecharger_recu)

        self.article_shop.receipt_requested.connect(self._telecharger_recu)
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
        self.chat_dialog.file_attach_requested.connect(self._on_chat_attach)
        self.chat_dialog.download_requested.connect(self._on_chat_download)

    def start(self):
        self.lock_screen.show_kiosk()
        self.process_guard.start()
        self.drive_manager.start()
        self.ws.start()

    def shutdown(self):
        self.process_guard.stop()
        self.drive_manager.stop()
        self.ws.stop()
        self.ws.wait(2000)

    def _on_disconnected(self):
        self.lock_screen.show_error("Connexion au serveur perdue, nouvelle tentative...")
        self.session_overlay.hide()
        self.lock_screen.show_kiosk()
        self._stop_surveillance()

    def _charger_charte(self):
        """Récupère la charte d'utilisation configurée (endpoint public du serveur) —
        best-effort : sans réponse, l'étape d'acceptation reste simplement masquée."""
        try:
            import requests
            r = requests.get(f"http://{self.config['server_url']}/portail/public/config", timeout=5)
            r.raise_for_status()
            charte = (r.json().get("data") or {}).get("charte") or ""
            self.lock_screen.set_charte(charte)
        except Exception:
            pass

    def _telecharger_recu(self, paiement_id: int):
        """Télécharge le reçu (ticket de caisse) du paiement dans le dossier de
        téléchargements de l'utilisateur et l'ouvre dans le navigateur."""
        import requests
        from pathlib import Path
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        try:
            r = requests.get(
                f"http://{self.config['server_url']}/portail/poste/recu/{paiement_id}",
                params={"poste_id": self.config["poste_id"], "token": self.config["token"]},
                timeout=10,
            )
            r.raise_for_status()
            dossier = Path.home() / "Downloads"
            dossier.mkdir(exist_ok=True)
            chemin = dossier / f"recu-{paiement_id}.html"
            chemin.write_bytes(r.content)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(chemin)))
        except Exception as e:
            QMessageBox.warning(None, "Reçu indisponible", str(e))

    def _rafraichir_recus(self):
        """Interroge la liste des reçus (forfaits, articles, recharges) du client
        actuellement connecté sur cette session — voir GET /portail/poste/paiements."""
        import requests

        try:
            r = requests.get(
                f"http://{self.config['server_url']}/portail/poste/paiements",
                params={"poste_id": self.config["poste_id"], "token": self.config["token"]},
                timeout=10,
            )
            r.raise_for_status()
            self.receipts_dialog.set_paiements(r.json().get("data", []))
        except Exception as e:
            self.receipts_dialog.show_error(f"Impossible de charger les reçus : {e}")

    def _open_storage(self):
        client = StorageClient(self.config["server_url"], self.config["poste_id"], self.config["token"])
        self.storage_dialog.set_client(client)
        self.storage_dialog.show()

    def _chat_client(self) -> ChatClient:
        return ChatClient(self.config["server_url"], self.config["poste_id"], self.config["token"])

    def _on_chat_attach(self, file_path: str, message_text: str):
        try:
            msg = self._chat_client().send_file(message_text, file_path, Path(file_path).name)
        except ChatError as e:
            QMessageBox.warning(self.chat_dialog, "Envoi impossible", str(e))
            return
        self.chat_dialog.add_message(msg)

    def _on_chat_download(self, message_id: int, suggested_name: str):
        dest_path, _ = QFileDialog.getSaveFileName(self.chat_dialog, "Enregistrer sous", suggested_name)
        if not dest_path:
            return
        try:
            self._chat_client().download_piece_jointe(message_id, dest_path)
        except ChatError as e:
            QMessageBox.warning(self.chat_dialog, "Téléchargement impossible", str(e))
            return
        QMessageBox.information(self.chat_dialog, "Téléchargement", "Fichier téléchargé avec succès.")

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

        elif msg_type == "tickets_choice_required":
            self.lock_screen.set_busy(False)
            ticket_id = TicketPickerDialog.choisir(data.get("tickets", []), self.lock_screen)
            if ticket_id is not None and self._pending_creds:
                username, password = self._pending_creds
                self.ws.send("session_request", {
                    "username": username, "password": password, "ticket_id": ticket_id,
                    "charte_acceptee": self.lock_screen.charte_acceptee(),
                })
            else:
                self.lock_screen.reset()

        elif msg_type == "session_limit_reached":
            self.lock_screen.set_busy(False)
            s = data.get("session_a_deconnecter", {})
            question = (
                f"Nombre maximum de connexions simultanées atteint "
                f"({data.get('portee')} : {data.get('limite')}).\n\n"
                f"Déconnecter la session sur « {s.get('poste_nom') or 'WiFi'} » pour continuer ?"
            )
            reponse = QMessageBox.question(
                self.lock_screen, "Limite de connexions atteinte", question,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reponse == QMessageBox.Yes:
                payload = {
                    "deconnecter_session_id": s.get("id"),
                    "charte_acceptee": self.lock_screen.charte_acceptee(),
                }
                if data.get("username") and self._pending_creds:
                    username, password = self._pending_creds
                    payload.update({"username": username, "password": password})
                elif data.get("code"):
                    payload["code"] = data.get("code")
                if data.get("ticket_id") is not None:
                    payload["ticket_id"] = data.get("ticket_id")
                self.ws.send("session_request", payload)
            else:
                self.lock_screen.reset()

        elif msg_type == "mes_tickets":
            tickets = data.get("tickets", [])
            if not tickets:
                QMessageBox.information(self.session_overlay, "Tickets", "Aucun autre ticket disponible sur ce compte.")
            else:
                ticket_id = TicketPickerDialog.choisir(tickets, self.session_overlay)
                if ticket_id is not None:
                    self.ws.send("changer_ticket_request", {"ticket_id": ticket_id})

        elif msg_type in ("session_ended", "lock"):
            self._exit_session()

        elif msg_type == "disable_kiosk":
            # Désactivation à distance déjà autorisée côté serveur (rôle admin/opérateur
            # + permission "postes" — voir router/poste.py), aucune re-vérification locale.
            logger.info("Kiosk désactivé à distance par l'administration")
            self._disable_kiosk()

        elif msg_type == "commande":
            # Commande système déjà autorisée côté serveur (rôle admin/opérateur +
            # permission "postes" — voir router/poste.py), aucune re-vérification locale.
            system_commands.executer_commande(data.get("commande", ""), data.get("details"))

        elif msg_type == "code_secours":
            # Mise en cache locale (hash uniquement) du code de secours pour le menu
            # admin — voir ui/admin_menu_dialog.py. Poussé à chaque (re)connexion et
            # à chaque génération à chaud (voir Poste_service.generer_code_secours).
            self.config["code_secours_hash"] = data.get("hash")
            self.config["code_secours_expire_le"] = data.get("expire_le")
            save_config(self.config)

        elif msg_type == "articles_list":
            self.article_shop.set_articles(data.get("articles", []))

        elif msg_type == "purchase_result":
            paiement_id = (data.get("achat") or {}).get("paiement_id")
            self.article_shop.show_purchase_result(data.get("success", False), data.get("message", ""), paiement_id)

        elif msg_type == "print_result":
            self.print_dialog.show_billing_result(data.get("success", False), data.get("message", ""))

        elif msg_type == "blocked_apps":
            self.process_guard.set_blocked_apps(data.get("apps", []))

        elif msg_type == "blocked_sites":
            hosts_manager.apply_blocked_domains(data.get("domaines", []))

        elif msg_type == "blocked_drives":
            self.drive_manager.set_blocked_types(data.get("types", []))

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

    def _on_disable_kiosk_requested(self):
        """Raccourci local (Ctrl+Alt+Shift+Q) : ouvre le menu admin (identifiants
        du compte Windows configuré, ou code de secours) — vérification 100%
        locale, fonctionne même sans connexion au serveur."""
        from ui.admin_menu_dialog import AdminMenuDialog

        action = AdminMenuDialog.demander_action(self.config, self.lock_screen)
        if action == AdminMenuDialog.ACTION_QUITTER_KIOSK:
            self._disable_kiosk()
        elif action == AdminMenuDialog.ACTION_RESET_RESEAU:
            self._reset_network_config()

    def _disable_kiosk(self):
        """Désactivation définitive du kiosk (admin local confirmé, ou commande
        distante déjà autorisée côté serveur) : relâche le hook clavier et ferme
        l'application — contrairement à hide_kiosk() seul (appelé par
        _enter_session), qui ne fait que céder temporairement la place à une
        session utilisateur légitime en laissant le kiosk actif en arrière-plan."""
        self.lock_screen.hide_kiosk()
        QApplication.instance().quit()

    def _reset_network_config(self):
        """Efface l'adresse serveur/ID/token du poste (compte admin conservé) et
        relance immédiatement le process pour rouvrir SetupDialog. Il n'existe
        aucun superviseur de process dans ce projet (voir
        packaging/kiosk_deployment.md) : on redémarre le process Python
        lui-même (os.execv) plutôt que de quitter et laisser le poste sans kiosk
        actif en attendant un hypothétique redémarrage externe."""
        import os

        self.config["server_url"] = ""
        self.config["poste_id"] = None
        self.config["token"] = None
        self.config["code_secours_hash"] = None
        self.config["code_secours_expire_le"] = None
        save_config(self.config)

        self.lock_screen.hide_kiosk()
        self.shutdown()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _on_login_submitted(self, username: str, password: str):
        self._pending_creds = (username, password)
        self.ws.send("session_request", {
            "username": username, "password": password,
            "charte_acceptee": self.lock_screen.charte_acceptee(),
        })

    def _enter_session(self, session_data: dict):
        self.current_session = session_data
        self.session_overlay.set_session(
            session_data.get("limite_minutes"),
            session_data.get("consommation_minutes", 0),
            session_data.get("limite_data_mo"),
            session_data.get("consommation_data_mo", 0),
        )
        # changer de ticket n'a de sens que pour une session rattachée à un compte
        self.session_overlay.set_change_ticket_visible(bool(session_data.get("user_id")))
        self.lock_screen.hide_kiosk()
        self.session_overlay.show_at_top_right()
        self._start_surveillance()

    def _exit_session(self):
        self.current_session = None
        self.storage_dialog.hide()
        self.session_overlay.hide()
        self.lock_screen.reset()
        self.lock_screen.show_kiosk()
        self._stop_surveillance()

    def _start_surveillance(self):
        self.surveillance_client = SurveillanceClient(
            self.config["server_url"], self.config["poste_id"], self.config["token"]
        )
        self._historique_watermark = datetime.now(timezone.utc)

        try:
            cfg = self.surveillance_client.get_config()
        except SurveillanceError as e:
            logger.warning("Config surveillance indisponible : %s", e)
            return

        if cfg.get("captures_actif") and cfg.get("captures_intervalle_secondes"):
            self._capture_timer.start(int(cfg["captures_intervalle_secondes"]) * 1000)
        if cfg.get("historique_actif") and cfg.get("historique_intervalle_secondes"):
            self._historique_timer.start(int(cfg["historique_intervalle_secondes"]) * 1000)

    def _stop_surveillance(self):
        self._capture_timer.stop()
        self._historique_timer.stop()
        self.surveillance_client = None

    def _on_capture_tick(self):
        if not self.surveillance_client:
            return
        png_bytes = capturer_ecran()
        if not png_bytes:
            return
        try:
            self.surveillance_client.envoyer_capture(png_bytes)
        except SurveillanceError as e:
            logger.warning("Échec envoi capture d'écran : %s", e)

    def _on_historique_tick(self):
        if not self.surveillance_client:
            return
        entrees = lire_historique_recent(self._historique_watermark)
        if not entrees:
            return
        # Avance le repère avant l'envoi (même en cas d'échec réseau) : cette fonctionnalité
        # est du suivi best-effort, pas un flux critique — mieux vaut perdre un lot ponctuel
        # que de re-scanner indéfiniment un historique qui grossit à chaque cycle.
        self._historique_watermark = max(
            datetime.fromisoformat(e["date_visite"]) for e in entrees
        )
        try:
            self.surveillance_client.envoyer_historique(entrees)
        except SurveillanceError as e:
            logger.warning("Échec envoi historique de navigation : %s", e)


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
