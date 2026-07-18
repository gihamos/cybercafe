"""Façade multiplateforme pour le durcissement kiosk (voir linux.py / windows.py).

install_hardening(window_id) : active le blocage des raccourcis d'évasion et les
    indications kiosk (masquage barre des tâches, always-on-top). À appeler quand
    l'écran de verrouillage est affiché (aucune session active).
uninstall_hardening() : relâche tout, à appeler dès qu'une session démarre pour
    rendre un usage normal du poste au client.
verify_admin_credentials(username, password) : valide un compte admin local
    (Windows uniquement pour l'instant — voir linux.py) sans connexion réseau,
    utilisé pour la désactivation locale du kiosk.
redemarrer_poste() / eteindre_poste() : commandes système élevées (voir
    core/system_commands.py et packaging/kiosk_deployment.md pour le niveau de
    privilège requis).
verrouiller_lecteur(identifiant) / deverrouiller_lecteur(identifiant) : bloque/
    débloque un lecteur (lettre sur Windows, point de montage sur Linux — voir
    les docstrings platform-spécifiques, la sémantique diffère par nature).
lecteurs_a_bloquer(types_bloques) : énumère les lecteurs actuellement présents
    dont le type (voir modèle TypeLecteur côté serveur) correspond à un des
    types bloqués — utilisé par core/drive_manager.py pour l'application
    continue (contrairement à verrouiller_lecteur/deverrouiller_lecteur qui
    agissent sur un identifiant déjà connu).
"""

import sys

if sys.platform == "win32":
    from platform_.windows import (
        install_hardening, uninstall_hardening, verify_admin_credentials,
        redemarrer_poste, eteindre_poste, verrouiller_lecteur, deverrouiller_lecteur,
        lecteurs_a_bloquer,
    )
elif sys.platform.startswith("linux"):
    from platform_.linux import (
        install_hardening, uninstall_hardening, verify_admin_credentials,
        redemarrer_poste, eteindre_poste, verrouiller_lecteur, deverrouiller_lecteur,
        lecteurs_a_bloquer,
    )
else:
    def install_hardening(window_id: int | None = None) -> bool:
        return False

    def uninstall_hardening():
        pass

    def verify_admin_credentials(username: str, password: str) -> bool:
        return False

    def redemarrer_poste():
        pass

    def eteindre_poste():
        pass

    def verrouiller_lecteur(identifiant: str):
        pass

    def deverrouiller_lecteur(identifiant: str):
        pass

    def lecteurs_a_bloquer(types_bloques: set[str]) -> set[str]:
        return set()
