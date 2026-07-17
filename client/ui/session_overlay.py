from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from ui.theme import QSS, DANGER, TEXT

LOW_TIME_THRESHOLD_SECONDS = 5 * 60


class SessionOverlay(QWidget):
    """Barre flottante affichée pendant qu'une session est active sur le poste."""

    buy_article_clicked = Signal()
    print_clicked = Signal()
    storage_clicked = Signal()
    chat_clicked = Signal()
    receipts_clicked = Signal()
    end_session_clicked = Signal()
    change_ticket_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(QSS)
        self.resize(620, 50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self.time_label = QLabel("--:--:--")
        self.time_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(self.time_label)

        self.data_label = QLabel("")
        self.data_label.setProperty("role", "subtitle")
        layout.addWidget(self.data_label)

        layout.addStretch()

        chat_btn = QPushButton("💬 Discuter")
        chat_btn.clicked.connect(self.chat_clicked.emit)
        layout.addWidget(chat_btn)

        storage_btn = QPushButton("📁 Stockage")
        storage_btn.clicked.connect(self.storage_clicked.emit)
        layout.addWidget(storage_btn)

        buy_btn = QPushButton("🛒 Boutique")
        buy_btn.clicked.connect(self.buy_article_clicked.emit)
        layout.addWidget(buy_btn)

        print_btn = QPushButton("🖨 Imprimer")
        print_btn.clicked.connect(self.print_clicked.emit)
        layout.addWidget(print_btn)

        receipts_btn = QPushButton("🧾 Mes reçus")
        receipts_btn.clicked.connect(self.receipts_clicked.emit)
        layout.addWidget(receipts_btn)

        self.change_ticket_btn = QPushButton("🎫 Changer de ticket")
        self.change_ticket_btn.clicked.connect(self.change_ticket_clicked.emit)
        self.change_ticket_btn.setVisible(False)  # affiché uniquement si un compte est connecté
        layout.addWidget(self.change_ticket_btn)

        end_btn = QPushButton("Terminer ma session")
        end_btn.setProperty("role", "danger")
        end_btn.clicked.connect(self.end_session_clicked.emit)
        layout.addWidget(end_btn)

        self._remaining_seconds: int | None = None
        self._remaining_mo: float | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def show_at_top_right(self):
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 10, geo.top() + 10)
        self.show()

    def set_session(
        self,
        limite_minutes: int | None,
        consommation_minutes: int,
        limite_data_mo: float | None,
        consommation_data_mo: float
    ):
        if limite_minutes is not None:
            self._remaining_seconds = max(0, (limite_minutes - (consommation_minutes or 0)) * 60)
        else:
            self._remaining_seconds = None

        if limite_data_mo is not None:
            self._remaining_mo = max(0.0, limite_data_mo - (consommation_data_mo or 0))
        else:
            self._remaining_mo = None

        self._refresh_labels()

    def _tick(self):
        if self._remaining_seconds is not None:
            self._remaining_seconds = max(0, self._remaining_seconds - 1)
            self._refresh_labels()

    def _refresh_labels(self):
        if self._remaining_seconds is not None:
            m, s = divmod(self._remaining_seconds, 60)
            h, m = divmod(m, 60)
            self.time_label.setText(f"{h:02d}:{m:02d}:{s:02d} restant")
            color = DANGER if self._remaining_seconds <= LOW_TIME_THRESHOLD_SECONDS else TEXT
            self.time_label.setStyleSheet(f"font-weight: 700; color: {color};")
        else:
            self.time_label.setText("Temps illimité")
            self.time_label.setStyleSheet(f"font-weight: 700; color: {TEXT};")

        if self._remaining_mo is not None:
            self.data_label.setText(f"{self._remaining_mo:.0f} Mo restants")
        else:
            self.data_label.setText("")

    def set_change_ticket_visible(self, visible: bool):
        self.change_ticket_btn.setVisible(visible)
