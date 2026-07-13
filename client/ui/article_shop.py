from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox
)

from ui.theme import QSS


class ArticleShopDialog(QDialog):
    """Boutique accessible depuis l'overlay de session : liste les articles actifs et
    permet d'en acheter un (débité du solde du client connecté sur cette session)."""

    refresh_requested = Signal()
    receipt_requested = Signal(int)
    buy_requested = Signal(int)   # article_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Boutique")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(QSS)
        self.resize(420, 480)

        layout = QVBoxLayout(self)

        title = QLabel("Boutique")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        self.info_label = QLabel("Chargement des articles...")
        self.info_label.setProperty("role", "subtitle")
        layout.addWidget(self.info_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.buy_btn = QPushButton("Acheter")
        self.buy_btn.setProperty("role", "primary")
        self.buy_btn.clicked.connect(self._on_buy_clicked)
        btn_row.addWidget(self.buy_btn)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        self.info_label.setText("Chargement des articles...")
        self.refresh_requested.emit()

    def set_articles(self, articles: list[dict]):
        self.list_widget.clear()
        self.info_label.setText("Sélectionnez un article :" if articles else "Aucun article disponible")

        for article in articles:
            label = f"{article['nom']} — {article['prix']:.2f}€"
            if article.get("categorie"):
                label += f" ({article['categorie']})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, article["id"])
            self.list_widget.addItem(item)

    def _on_buy_clicked(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un article.")
            return

        self.buy_btn.setEnabled(False)
        self.buy_requested.emit(item.data(Qt.UserRole))

    def show_purchase_result(self, success: bool, message: str, paiement_id: int | None = None):
        self.buy_btn.setEnabled(True)
        if not success:
            QMessageBox.warning(self, "Achat impossible", message)
            return

        if paiement_id is None:
            QMessageBox.information(self, "Achat", message)
            return

        # proposer le téléchargement du reçu (ticket de caisse)
        box = QMessageBox(self)
        box.setWindowTitle("Achat")
        box.setText(message)
        recu_btn = box.addButton("Télécharger le reçu", QMessageBox.ActionRole)
        box.addButton("Fermer", QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() is recu_btn:
            self.receipt_requested.emit(paiement_id)
