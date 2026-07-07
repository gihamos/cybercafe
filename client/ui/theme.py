"""Palette et feuille de style partagées par tous les écrans du kiosk : un seul
endroit à modifier pour changer l'apparence de l'application cliente."""

BG = "#0b1120"
SURFACE = "#141b2d"
SURFACE_ALT = "#1b2438"
BORDER = "#2a3450"
TEXT = "#e7e9ee"
TEXT_MUTED = "#8b93a7"
ACCENT = "#4f6df5"
ACCENT_HOVER = "#3d58d6"
DANGER = "#f87171"
SUCCESS = "#34d399"
WARNING = "#fbbf24"

QSS = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-size: 14px;
    font-family: "Segoe UI", "Inter", sans-serif;
}}
QDialog {{ background-color: {BG}; }}

QLabel[role="title"] {{ font-size: 26px; font-weight: 700; }}
QLabel[role="subtitle"] {{ color: {TEXT_MUTED}; font-size: 14px; }}
QLabel[role="section"] {{ color: {TEXT_MUTED}; font-size: 12px; font-weight: 600; letter-spacing: 0.04em; }}
QLabel[role="error"] {{ color: {DANGER}; font-weight: 600; }}
QLabel[role="success"] {{ color: {SUCCESS}; font-weight: 600; }}

QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 10px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}

QPushButton {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    color: {TEXT};
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #232d47; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; }}

QPushButton[role="primary"] {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    color: white;
}}
QPushButton[role="primary"]:hover {{ background-color: {ACCENT_HOVER}; }}

QPushButton[role="danger"] {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
}}
QPushButton[role="danger"]:hover {{ background-color: rgba(248, 113, 113, 0.12); }}

QPushButton[role="ghost"] {{
    background-color: transparent;
    border: none;
    color: {TEXT_MUTED};
}}
QPushButton[role="ghost"]:hover {{ color: {TEXT}; }}

QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: {SURFACE_ALT}; padding: 9px 18px; color: {TEXT_MUTED};
    border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
    font-weight: 600;
}}
QTabBar::tab:selected {{ background: {ACCENT}; color: white; }}

QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{ padding: 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background-color: {ACCENT}; color: white; }}

QProgressBar {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    height: 14px;
    text-align: center;
    color: {TEXT};
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 7px; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; }}
"""


def refresh_style(widget):
    """À appeler après avoir changé une propriété dynamique (ex: [role]) pour que le
    style Qt (basé sur QSS) soit réévalué sur ce widget."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
