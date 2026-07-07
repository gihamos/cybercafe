import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QCheckBox, QRadioButton, QButtonGroup, QSpinBox, QMessageBox
)

from ui.theme import QSS

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def _count_pages(file_path: str) -> int:
    """Compte les pages pour un PDF ; pour les autres formats (image, texte, docx...)
    impossible à déterminer sans dépendance lourde supplémentaire, on part de 1 page
    et l'opérateur/le client peut corriger manuellement via le champ à côté."""
    if file_path.lower().endswith(".pdf") and PdfReader is not None:
        try:
            return len(PdfReader(file_path).pages)
        except Exception:
            pass
    return 1


def _print_native(file_path: str) -> tuple[bool, str]:
    """Envoie le fichier au spouleur d'impression du système (imprimante par défaut).
    Le rendu (mise en page, recto-verso réel, couleur réelle) dépend ensuite du pilote
    d'imprimante et de l'application associée au type de fichier : recto_verso et
    type_impression choisis ici servent surtout à la facturation côté serveur."""
    try:
        if sys.platform == "win32":
            os.startfile(file_path, "print")
        else:
            subprocess.run(["lp", file_path], check=True, capture_output=True)
        return True, "Document envoyé à l'imprimante"
    except Exception as e:
        return False, f"Échec de l'impression : {e}"


class PrintDialog(QDialog):
    """Impression locale (spouleur du poste) + facturation via le serveur."""

    billing_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Imprimer un document")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(QSS)
        self.resize(420, 280)
        self._file_path: str | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Imprimer un document")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        pick_row = QHBoxLayout()
        self.file_label = QLabel("Aucun fichier sélectionné")
        pick_btn = QPushButton("Choisir un fichier...")
        pick_btn.clicked.connect(self._pick_file)
        pick_row.addWidget(self.file_label, 1)
        pick_row.addWidget(pick_btn)
        layout.addLayout(pick_row)

        pages_row = QHBoxLayout()
        pages_row.addWidget(QLabel("Nombre de pages :"))
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 1000)
        pages_row.addWidget(self.pages_spin)
        layout.addLayout(pages_row)

        self.recto_verso_check = QCheckBox("Recto-verso")
        layout.addWidget(self.recto_verso_check)

        color_row = QHBoxLayout()
        self.nb_radio = QRadioButton("Noir & blanc")
        self.color_radio = QRadioButton("Couleur")
        self.nb_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.nb_radio)
        group.addButton(self.color_radio)
        color_row.addWidget(self.nb_radio)
        color_row.addWidget(self.color_radio)
        layout.addLayout(color_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.print_btn = QPushButton("Imprimer")
        self.print_btn.setProperty("role", "primary")
        self.print_btn.clicked.connect(self._on_print_clicked)
        btn_row.addWidget(self.print_btn)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        self.status_label.setText("")
        self.print_btn.setEnabled(True)

    def _pick_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un document",
            str(Path.home()),
            "Documents (*.pdf *.txt *.png *.jpg *.jpeg *.docx *.odt);;Tous les fichiers (*)"
        )
        if not file_path:
            return
        self._file_path = file_path
        self.file_label.setText(Path(file_path).name)
        self.pages_spin.setValue(_count_pages(file_path))

    def _on_print_clicked(self):
        if not self._file_path:
            QMessageBox.warning(self, "Aucun fichier", "Veuillez choisir un fichier à imprimer.")
            return

        self.print_btn.setEnabled(False)
        self.status_label.setText("Impression en cours...")

        success, message = _print_native(self._file_path)
        self.status_label.setText(message)

        if success:
            self.billing_requested.emit({
                "fichier_nom": Path(self._file_path).name,
                "pages_total": self.pages_spin.value(),
                "type_impression": "couleur" if self.color_radio.isChecked() else "noir_blanc",
                "recto_verso": self.recto_verso_check.isChecked(),
            })
        else:
            self.print_btn.setEnabled(True)

    def show_billing_result(self, success: bool, message: str):
        self.print_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Facturation", message)
            self.close()
        else:
            QMessageBox.warning(self, "Facturation impossible", message)
