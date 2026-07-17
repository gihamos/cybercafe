from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox
)

from ui.theme import QSS

NATURE_LABEL = {"forfait": "Forfait", "article": "Article", "credit": "Recharge"}


class ReceiptsDialog(QDialog):
    """Historique des reçus (forfaits, articles, recharges) du client connecté sur
    cette session — accessible depuis l'overlay de session, comme la boutique."""

    refresh_requested = Signal()
    receipt_requested = Signal(int)  # paiement_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mes reçus")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(QSS)
        self.resize(460, 500)

        layout = QVBoxLayout(self)

        title = QLabel("Tickets & factures")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        self.info_label = QLabel("Chargement...")
        self.info_label.setProperty("role", "subtitle")
        layout.addWidget(self.info_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.download_btn = QPushButton("Télécharger le reçu")
        self.download_btn.setProperty("role", "primary")
        self.download_btn.clicked.connect(self._on_download_clicked)
        btn_row.addWidget(self.download_btn)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        self.info_label.setText("Chargement...")
        self.refresh_requested.emit()

    def set_paiements(self, paiements: list[dict]):
        self.list_widget.clear()
        self.info_label.setText("Sélectionnez un reçu à télécharger :" if paiements else "Aucun règlement pour le moment")

        for p in paiements:
            nature = NATURE_LABEL.get(p.get("nature"), p.get("nature", ""))
            label = f"{p.get('libelle') or nature} — {p['montant']:.2f}€ ({p['statut']})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, p["id"])
            item.setData(Qt.UserRole + 1, p.get("statut"))
            self.list_widget.addItem(item)

    def show_error(self, message: str):
        self.info_label.setText(message)

    def _on_download_clicked(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un reçu.")
            return
        if item.data(Qt.UserRole + 1) != "succes":
            QMessageBox.warning(self, "Reçu indisponible", "Ce règlement n'est pas (encore) confirmé.")
            return
        self.receipt_requested.emit(item.data(Qt.UserRole))
