"""Durcissement kiosk pour Windows.

Utilise un hook clavier bas niveau (WH_KEYBOARD_LL) via ctypes pour intercepter et
avaler les raccourcis d'évasion (Alt+Tab, touche Windows, Alt+F4, Ctrl+Echap).

Limite connue : Ctrl+Alt+Suppr (Secure Attention Sequence) ne peut PAS être
intercepté depuis une application utilisateur, quel que soit le hook posé — c'est
une protection du noyau Windows conçue précisément pour empêcher ça. Pour le
neutraliser il faut une stratégie de groupe / clé de registre dédiée sur le compte
kiosque (voir packaging/windows_kiosk_account.md).

⚠️ Ce module masquait auparavant la barre des tâches Windows (SW_HIDE sur
Shell_TrayWnd). Retiré délibérément : ce window handle appartient à explorer.exe,
un processus tiers de longue durée — rien dans le cycle de vie du kiosk ne
garantit sa restauration en cas d'arrêt anormal (crash, kill -9/taskkill /F,
coupure de courant), contrairement au hook clavier ci-dessous que Windows
nettoie automatiquement à la terminaison du processus, y compris un kill forcé.
Un incident réel (barre des tâches restée masquée après un simple test suivi
d'un taskkill /F) a confirmé ce risque : la fenêtre kiosk plein écran + toujours
au premier plan, combinée au hook clavier ci-dessous, suffit à bloquer les
tentatives d'évasion casuelles sans introduire un état système persistant et
irrécupérable par l'application elle-même.
"""

import ctypes
import subprocess
import winreg
from ctypes import wintypes

_IS_WINDOWS = True
try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32
except (AttributeError, OSError):
    _IS_WINDOWS = False

LOGON32_LOGON_INTERACTIVE = 2
LOGON32_PROVIDER_DEFAULT = 0

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_F4 = 0x73
VK_MENU = 0x12      # Alt
VK_CONTROL = 0x11

_BLOCKED_VKS = {VK_LWIN, VK_RWIN}


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


_state = {"hook": None, "proc": None}

if _IS_WINDOWS:
    _HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
else:
    _HOOKPROC = None


def _low_level_keyboard_proc(nCode, wParam, lParam):
    if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
        kb = ctypes.cast(lParam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
        alt_down = user32.GetAsyncKeyState(VK_MENU) & 0x8000
        ctrl_down = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000

        bloquer = (
            kb.vkCode in _BLOCKED_VKS
            or (alt_down and kb.vkCode in (VK_TAB, VK_F4, VK_ESCAPE))
            or (ctrl_down and kb.vkCode == VK_ESCAPE)
        )
        if bloquer:
            return 1

    return user32.CallNextHookEx(_state["hook"], nCode, wParam, lParam)


def install_hardening(window_id: int | None = None) -> bool:
    if not _IS_WINDOWS:
        return False

    if _state["hook"] is None:
        _state["proc"] = _HOOKPROC(_low_level_keyboard_proc)
        _state["hook"] = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, _state["proc"], kernel32.GetModuleHandleW(None), 0
        )

    return _state["hook"] is not None


def uninstall_hardening():
    if not _IS_WINDOWS:
        return
    if _state["hook"] is not None:
        user32.UnhookWindowsHookEx(_state["hook"])
        _state["hook"] = None
        _state["proc"] = None


def verify_admin_credentials(username: str, password: str) -> bool:
    """Valide un identifiant + mot de passe contre un compte Windows local via
    l'API LogonUserW (authentification SAM locale). Ne change pas de session ni
    de bureau actif, aucun appel réseau — utilisé par la désactivation locale du
    kiosk (voir ui/admin_menu_dialog.py) pour fonctionner même hors ligne."""
    if not _IS_WINDOWS or not username or not password:
        return False

    token = wintypes.HANDLE()
    ok = advapi32.LogonUserW(
        username, ".", password,
        LOGON32_LOGON_INTERACTIVE, LOGON32_PROVIDER_DEFAULT,
        ctypes.byref(token),
    )
    if ok:
        kernel32.CloseHandle(token)
    return bool(ok)


# ---------------------------------------------------------------------------
# Commandes système à privilèges élevés (voir core/system_commands.py) — le
# process client doit tourner avec des droits suffisants pour ces appels
# (voir packaging/kiosk_deployment.md § Niveau de privilège requis).
# ---------------------------------------------------------------------------

def redemarrer_poste():
    """Redémarre le poste avec un court délai de grâce (5s, laisse le temps à
    d'éventuels processus de se terminer proprement). Nécessite
    SE_SHUTDOWN_NAME — accordé par défaut aux utilisateurs standards sur un
    poste de travail Windows (contrairement à Windows Server)."""
    if not _IS_WINDOWS:
        return
    subprocess.run(["shutdown", "/r", "/t", "5"], check=False)


def eteindre_poste():
    """Éteint le poste avec un court délai de grâce (5s)."""
    if not _IS_WINDOWS:
        return
    subprocess.run(["shutdown", "/s", "/t", "5"], check=False)


_EXPLORER_POLICIES_PATH = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"


def _lettre_vers_bit(lettre: str) -> int:
    return 1 << (ord(lettre.strip().upper()[0]) - ord("A"))


def _lire_no_drives() -> int:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _EXPLORER_POLICIES_PATH) as key:
            valeur, _ = winreg.QueryValueEx(key, "NoDrives")
            return valeur
    except FileNotFoundError:
        return 0


def _ecrire_no_drives(valeur: int):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_POLICIES_PATH) as key:
        winreg.SetValueEx(key, "NoDrives", 0, winreg.REG_DWORD, valeur)


def verrouiller_lecteur(lettre: str):
    """Masque le lecteur dans l'explorateur Windows via la stratégie NoDrives
    (bitmask HKCU, un bit par lettre A-Z, compte kiosque standard — pas besoin
    de droits admin). ⚠️ Ne bloque QUE l'interface Explorer (y compris les
    boîtes de dialogue ouvrir/enregistrer d'autres applications, qui utilisent
    les mêmes API shell) — n'empêche pas un accès en ligne de commande ou par
    une application qui contourne le shell. Pour un blocage réel au niveau
    matériel/pilote, voir packaging/kiosk_deployment.md.

    Prend effet au prochain redémarrage d'explorer.exe ou à la prochaine
    connexion — volontairement PAS forcé automatiquement ici (voir plus haut
    dans ce fichier : manipuler explorer.exe sans garantie de restauration a
    déjà causé un incident réel sur ce projet)."""
    if not _IS_WINDOWS:
        return
    _ecrire_no_drives(_lire_no_drives() | _lettre_vers_bit(lettre))


def deverrouiller_lecteur(lettre: str):
    if not _IS_WINDOWS:
        return
    _ecrire_no_drives(_lire_no_drives() & ~_lettre_vers_bit(lettre))


# ---------------------------------------------------------------------------
# Blocage continu par type de lecteur (voir core/drive_manager.py) — l'énumération
# des lettres présentes et leur type se fait à chaque tick, contrairement au
# verrouillage ponctuel ci-dessus qui prend une lettre déjà connue en paramètre.
# ---------------------------------------------------------------------------

DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5

_TYPE_VERS_DRIVE_TYPE = {
    "amovible": DRIVE_REMOVABLE,
    "cd_dvd": DRIVE_CDROM,
    "reseau": DRIVE_REMOTE,
}


def lecteurs_a_bloquer(types_bloques: set[str]) -> set[str]:
    """Renvoie l'ensemble des lettres actuellement présentes sur le poste dont le
    type correspond à un des types bloqués (voir TypeLecteur côté serveur :
    "amovible", "cd_dvd", "reseau"). DRIVE_FIXED n'est structurellement jamais
    concerné : le lecteur système ne peut pas être verrouillé par construction,
    quel que soit le contenu de types_bloques."""
    if not _IS_WINDOWS or not types_bloques:
        return set()

    drive_types_bloques = {
        _TYPE_VERS_DRIVE_TYPE[t] for t in types_bloques if t in _TYPE_VERS_DRIVE_TYPE
    }
    if not drive_types_bloques:
        return set()

    lettres = set()
    mask = kernel32.GetLogicalDrives()
    for i in range(26):
        if not (mask & (1 << i)):
            continue
        lettre = chr(ord("A") + i)
        drive_type = kernel32.GetDriveTypeW(f"{lettre}:\\")
        if drive_type == DRIVE_FIXED:
            continue
        if drive_type in drive_types_bloques:
            lettres.add(lettre)
    return lettres
