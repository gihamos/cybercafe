from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QButtonGroup, QStackedWidget
)


class PayConnectTab(QWidget):
    """Onglet 'Connexion rapide' de l'écran de verrouillage : payer une durée choisie
    sans ticket ni abonnement, soit via le solde du compte (instantané), soit en
    espèces au comptoir (l'opérateur encaisse et valide à distance). Non transférable
    et sans conservation des minutes non consommées — un raccourci pour une session
    ponctuelle sur ce poste."""

    tarifs_requested = Signal()
    solde_submitted = Signal(str, str, int)   # username, password, minutes
    especes_submitted = Signal(int)           # minutes
    cancel_requested = Signal(int)            # request_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minutes: int | None = None
        self._request_id: int | None = None

        root = QVBoxLayout(self)

        subtitle = QLabel("Choisissez une durée pour vous connecter tout de suite sur ce poste.")
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self._tarifs_row = QHBoxLayout()
        self._tarifs_group = QButtonGroup(self)
        self._tarifs_group.buttonClicked.connect(self._on_tarif_clicked)
        root.addLayout(self._tarifs_row)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        # --- Page 0 : choix du moyen de paiement ---
        choice_page = QWidget()
        choice_layout = QVBoxLayout(choice_page)
        self.selected_label = QLabel("")
        self.selected_label.setStyleSheet("font-weight: 600;")
        choice_layout.addWidget(self.selected_label)

        solde_btn = QPushButton("Payer avec mon solde")
        solde_btn.setProperty("role", "primary")
        solde_btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        choice_layout.addWidget(solde_btn)

        especes_btn = QPushButton("Payer en espèces au comptoir")
        especes_btn.clicked.connect(self._submit_especes)
        choice_layout.addWidget(especes_btn)
        choice_layout.addStretch()
        self._stack.addWidget(choice_page)

        # --- Page 1 : paiement par solde (identifiants) ---
        solde_page = QWidget()
        solde_layout = QVBoxLayout(solde_page)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self._submit_solde)
        solde_layout.addWidget(self.username_input)
        solde_layout.addWidget(self.password_input)

        valider_btn = QPushButton("Valider et se connecter")
        valider_btn.setProperty("role", "primary")
        valider_btn.clicked.connect(self._submit_solde)
        solde_layout.addWidget(valider_btn)

        back_btn = QPushButton("Retour")
        back_btn.setProperty("role", "ghost")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        solde_layout.addWidget(back_btn)
        solde_layout.addStretch()
        self._stack.addWidget(solde_page)

        # --- Page 2 : en attente de confirmation opérateur ---
        waiting_page = QWidget()
        waiting_layout = QVBoxLayout(waiting_page)
        self.waiting_label = QLabel("En attente de la confirmation de l'opérateur...")
        self.waiting_label.setWordWrap(True)
        waiting_layout.addWidget(self.waiting_label)

        cancel_btn = QPushButton("Annuler la demande")
        cancel_btn.setProperty("role", "danger")
        cancel_btn.clicked.connect(self._cancel)
        waiting_layout.addWidget(cancel_btn)
        waiting_layout.addStretch()
        self._stack.addWidget(waiting_page)

        self._reset_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.tarifs_requested.emit()

    def _reset_ui(self):
        self._stack.setCurrentIndex(0)
        self.password_input.clear()
        self.error_label.setText("")

    def set_tarifs(self, tarifs: list[dict]):
        for btn in self._tarifs_group.buttons():
            self._tarifs_group.removeButton(btn)
            btn.deleteLater()
        while self._tarifs_row.count():
            item = self._tarifs_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for tarif in tarifs:
            minutes = tarif["minutes"]
            label = f"{minutes} min\n{tarif['prix']:.2f}€"
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("minutes", minutes)
            self._tarifs_group.addButton(btn)
            self._tarifs_row.addWidget(btn)

    def _on_tarif_clicked(self, btn):
        self._minutes = btn.property("minutes")
        self.selected_label.setText(f"Durée sélectionnée : {self._minutes} minutes")
        self.error_label.setText("")
        self._stack.setCurrentIndex(0)

    def _submit_solde(self):
        if not self._minutes:
            return
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.error_label.setText("Veuillez saisir vos identifiants")
            return
        self.solde_submitted.emit(username, password, self._minutes)

    def _submit_especes(self):
        if not self._minutes:
            self.error_label.setText("Veuillez d'abord choisir une durée")
            return
        self.especes_submitted.emit(self._minutes)

    def show_pending(self, request_id: int, montant: float):
        self._request_id = request_id
        self.waiting_label.setText(
            f"Demande envoyée : {self._minutes} min ({montant:.2f}€).\n"
            "Merci de régler en espèces au comptoir — la session démarrera dès validation "
            "par l'opérateur."
        )
        self._stack.setCurrentIndex(2)

    def _cancel(self):
        if self._request_id is not None:
            self.cancel_requested.emit(self._request_id)
        self._request_id = None
        self._reset_ui()

    def show_error(self, message: str):
        self.error_label.setText(message)
        self._stack.setCurrentIndex(0)

    def show_refused(self):
        self._request_id = None
        self.error_label.setText("Votre demande a été refusée par l'opérateur.")
        self._stack.setCurrentIndex(0)

    def reset(self):
        self._request_id = None
        self._reset_ui()
