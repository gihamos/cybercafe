from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox
)


class ArticleShopDialog(QDialog):
    """Boutique accessible depuis l'overlay de session : liste les articles actifs et
    permet d'en acheter un (débité du solde du client connecté sur cette session)."""

    refresh_requested = Signal()
    buy_requested = Signal(int)   # article_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Boutique")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(420, 480)

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Chargement des articles...")
        layout.addWidget(self.info_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.buy_btn = QPushButton("Acheter")
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

    def show_purchase_result(self, success: bool, message: str):
        self.buy_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Achat", message)
        else:
            QMessageBox.warning(self, "Achat impossible", message)
