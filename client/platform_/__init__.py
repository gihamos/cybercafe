"""Façade multiplateforme pour le durcissement kiosk (voir linux.py / windows.py).

install_hardening(window_id) : active le blocage des raccourcis d'évasion et les
    indications kiosk (masquage barre des tâches, always-on-top). À appeler quand
    l'écran de verrouillage est affiché (aucune session active).
uninstall_hardening() : relâche tout, à appeler dès qu'une session démarre pour
    rendre un usage normal du poste au client.
"""

import sys

if sys.platform == "win32":
    from platform_.windows import install_hardening, uninstall_hardening
elif sys.platform.startswith("linux"):
    from platform_.linux import install_hardening, uninstall_hardening
else:
    def install_hardening(window_id: int | None = None) -> bool:
        return False

    def uninstall_hardening():
        pass
