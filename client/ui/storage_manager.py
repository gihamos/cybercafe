from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QProgressBar, QMessageBox, QFileDialog
)

from core.storage_client import StorageClient, StorageError
from ui.theme import QSS


def _human_size(octets: int) -> str:
    mo = octets / (1024 * 1024)
    if mo < 1:
        return f"{octets / 1024:.0f} Ko"
    return f"{mo:.1f} Mo"


class StorageDialog(QDialog):
    """Espace de stockage réseau de la session en cours (compte ou ticket) : upload,
    liste, téléchargement, suppression. Le stockage lié à un ticket est temporaire et
    sera automatiquement vidé par le serveur à la fin de la session (voir bandeau)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mon espace de stockage")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(QSS)
        self.resize(440, 520)
        self.client: StorageClient | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Mon espace de stockage")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        self.temp_notice = QLabel("")
        self.temp_notice.setProperty("role", "subtitle")
        self.temp_notice.setWordWrap(True)
        layout.addWidget(self.temp_notice)

        self.quota_bar = QProgressBar()
        self.quota_bar.setRange(0, 100)
        layout.addWidget(self.quota_bar)

        self.quota_label = QLabel("")
        self.quota_label.setProperty("role", "subtitle")
        layout.addWidget(self.quota_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        actions_row = QHBoxLayout()
        upload_btn = QPushButton("Envoyer un fichier...")
        upload_btn.setProperty("role", "primary")
        upload_btn.clicked.connect(self._on_upload)
        actions_row.addWidget(upload_btn)

        download_btn = QPushButton("Télécharger")
        download_btn.clicked.connect(self._on_download)
        actions_row.addWidget(download_btn)

        delete_btn = QPushButton("Supprimer")
        delete_btn.setProperty("role", "danger")
        delete_btn.clicked.connect(self._on_delete)
        actions_row.addWidget(delete_btn)
        layout.addLayout(actions_row)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self._fichiers: dict[int, dict] = {}

    def set_client(self, client: StorageClient):
        self.client = client

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        if not self.client:
            return
        try:
            quota = self.client.get_quota()
            fichiers = self.client.lister_fichiers()
        except StorageError as e:
            QMessageBox.warning(self, "Stockage indisponible", str(e))
            return

        self.temp_notice.setText(
            "Stockage temporaire : ces fichiers seront supprimés à la fin de votre session."
            if quota.get("temporaire") else
            "Stockage lié à votre compte : accessible depuis n'importe quel poste."
        )

        quota_mo = quota["quota_mo"]
        usage_mo = quota["usage_octets"] / (1024 * 1024)
        pct = min(100, int(usage_mo / quota_mo * 100)) if quota_mo else 0
        self.quota_bar.setValue(pct)
        self.quota_label.setText(f"{usage_mo:.1f} Mo utilisés sur {quota_mo:.0f} Mo")

        self.list_widget.clear()
        self._fichiers = {f["id"]: f for f in fichiers}
        for f in fichiers:
            item = QListWidgetItem(f"{f['nom_original']} — {_human_size(f['taille_octets'])}")
            item.setData(Qt.UserRole, f["id"])
            self.list_widget.addItem(item)

    def _selected_id(self) -> int | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _on_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier à envoyer")
        if not file_path:
            return
        try:
            self.client.upload(file_path, Path(file_path).name)
        except StorageError as e:
            QMessageBox.warning(self, "Envoi impossible", str(e))
            return
        self.refresh()

    def _on_download(self):
        fichier_id = self._selected_id()
        if fichier_id is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un fichier.")
            return

        nom = self._fichiers[fichier_id]["nom_original"]
        dest_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", nom)
        if not dest_path:
            return
        try:
            self.client.download(fichier_id, dest_path)
        except StorageError as e:
            QMessageBox.warning(self, "Téléchargement impossible", str(e))
            return
        QMessageBox.information(self, "Téléchargement", "Fichier téléchargé avec succès.")

    def _on_delete(self):
        fichier_id = self._selected_id()
        if fichier_id is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un fichier.")
            return

        if QMessageBox.question(self, "Confirmer", "Supprimer ce fichier ?") != QMessageBox.Yes:
            return
        try:
            self.client.supprimer(fichier_id)
        except StorageError as e:
            QMessageBox.warning(self, "Suppression impossible", str(e))
            return
        self.refresh()
