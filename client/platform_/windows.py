"""Durcissement kiosk pour Windows.

Utilise un hook clavier bas niveau (WH_KEYBOARD_LL) via ctypes pour intercepter et
avaler les raccourcis d'évasion (Alt+Tab, touche Windows, Alt+F4, Ctrl+Echap), et
masque la barre des tâches pendant que le kiosk tourne.

Limite connue : Ctrl+Alt+Suppr (Secure Attention Sequence) ne peut PAS être
intercepté depuis une application utilisateur, quel que soit le hook posé — c'est
une protection du noyau Windows conçue précisément pour empêcher ça. Pour le
neutraliser il faut une stratégie de groupe / clé de registre dédiée sur le compte
kiosque (voir packaging/windows_kiosk_account.md).

⚠️ Code non testé en conditions réelles dans cet environnement de développement
(pas de machine Windows disponible) : à valider sur un vrai poste Windows avant
mise en production.
"""

import ctypes
from ctypes import wintypes

_IS_WINDOWS = True
try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except (AttributeError, OSError):
    _IS_WINDOWS = False

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

SW_HIDE = 0
SW_SHOW = 5

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

    _hide_taskbar()
    return _state["hook"] is not None


def uninstall_hardening():
    if not _IS_WINDOWS:
        return
    if _state["hook"] is not None:
        user32.UnhookWindowsHookEx(_state["hook"])
        _state["hook"] = None
        _state["proc"] = None
    _show_taskbar()


def _find_taskbar_hwnd():
    return user32.FindWindowW("Shell_TrayWnd", None)


def _hide_taskbar():
    hwnd = _find_taskbar_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, SW_HIDE)


def _show_taskbar():
    hwnd = _find_taskbar_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, SW_SHOW)
