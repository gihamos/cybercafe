from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton
from PySide6.QtCore import Qt

from ui.theme import QSS


class TicketPickerDialog(QDialog):
    """Choix du ticket à utiliser — un client peut posséder plusieurs tickets actifs
    (achetés en caisse ou en ligne) et changer à tout moment, y compris pendant
    qu'une session est déjà en cours sur ce poste."""

    def __init__(self, tickets: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choisir un ticket")
        self.setStyleSheet(QSS)
        self.resize(420, 360)
        self.ticket_id: int | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Sélectionnez le ticket à utiliser :"))

        self.list_widget = QListWidget()
        for t in tickets:
            restant = []
            if t.get("restant_minutes") is not None:
                restant.append(f"{t['restant_minutes']} min")
            if t.get("restant_data_mo") is not None:
                restant.append(f"{t['restant_data_mo']:.0f} Mo")
            label = f"{t.get('offre_nom') or 'Ticket'} — {t['code']}"
            if restant:
                label += f" ({', '.join(restant)})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t["id"])
            self.list_widget.addItem(item)
        self.list_widget.itemDoubleClicked.connect(self._on_confirm)
        layout.addWidget(self.list_widget)

        confirm_btn = QPushButton("Utiliser ce ticket")
        confirm_btn.setProperty("role", "primary")
        confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _on_confirm(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        self.ticket_id = item.data(Qt.UserRole)
        self.accept()

    @staticmethod
    def choisir(tickets: list[dict], parent=None) -> int | None:
        dialog = TicketPickerDialog(tickets, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.ticket_id
        return None
