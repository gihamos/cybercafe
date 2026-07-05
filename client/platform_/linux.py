"""Durcissement kiosk pour Linux/X11.

Repose sur python-xlib : capture (best-effort) des raccourcis d'évasion courants via
XGrabKey, et pose des indications EWMH (skip taskbar/pager, always-on-top) sur la
fenêtre de l'app. Le blocage des raccourcis n'est réellement garanti que dans la
session X dédiée au kiosque (aucun autre gestionnaire de fenêtres pour les
revendiquer en premier) — voir packaging/linux_kiosk_session/. Sur un bureau
classique (GNOME/KDE/XFCE...), certains raccourcis peuvent déjà être accaparés par
le WM et échapper à ce blocage : c'est une limitation connue, pas un bug.

Ne fait rien (et n'échoue pas) si aucun serveur X n'est joignable (ex: Wayland pur,
ou environnement headless) : toutes les fonctions sont no-op dans ce cas.
"""

from PySide6.QtCore import QSocketNotifier

try:
    from Xlib import X, XK, display
    from Xlib.protocol import event as xevent
    _XLIB_AVAILABLE = True
except ImportError:
    _XLIB_AVAILABLE = False


_state = {
    "display": None,
    "notifier": None,
    "grabbed": False,
}

# (keysym, modifiers) à intercepter. AnyModifier n'est volontairement pas utilisé
# pour rester ciblé sur des combinaisons précises.
_KEYSYMS_A_BLOQUER = [
    ("Tab", X.Mod1Mask),                       # Alt+Tab
    ("Tab", X.Mod1Mask | X.ShiftMask),         # Alt+Shift+Tab
    ("Escape", X.Mod1Mask),                    # Alt+Echap
    ("Escape", X.ControlMask),                 # Ctrl+Echap (menu demarrer XFCE/KDE)
    ("F4", X.Mod1Mask),                        # Alt+F4
    ("Super_L", 0),
    ("Super_R", 0),
    ("t", X.ControlMask | X.Mod1Mask),         # Ctrl+Alt+T (terminal, tres repandu)
]


def _get_display():
    if _state["display"] is not None:
        return _state["display"]
    try:
        _state["display"] = display.Display()
    except Exception:
        _state["display"] = False
    return _state["display"] or None


def install_hardening(window_id: int | None = None):
    """Tente de bloquer les raccourcis d'évasion et pose les hints EWMH kiosk.
    Silencieux (no-op) si aucun serveur X n'est disponible."""
    if not _XLIB_AVAILABLE:
        return False

    dpy = _get_display()
    if not dpy:
        return False

    root = dpy.screen().root
    root.change_attributes(event_mask=X.KeyPressMask)

    for keyname, modifiers in _KEYSYMS_A_BLOQUER:
        keysym = XK.string_to_keysym(keyname)
        keycode = dpy.keysym_to_keycode(keysym)
        if not keycode:
            continue
        try:
            root.grab_key(keycode, modifiers, True, X.GrabModeAsync, X.GrabModeAsync)
        except Exception:
            pass  # combo déjà accaparée par le WM en place : limitation connue

    dpy.flush()
    _state["grabbed"] = True

    # Draine les evenements X (KeyPress captures) sans bloquer la boucle Qt
    if _state["notifier"] is None:
        notifier = QSocketNotifier(dpy.fileno(), QSocketNotifier.Read)
        notifier.activated.connect(_drain_events)
        _state["notifier"] = notifier

    if window_id:
        _apply_ewmh_hints(dpy, window_id)

    return True


def uninstall_hardening():
    if not _XLIB_AVAILABLE or not _state["grabbed"]:
        return
    dpy = _get_display()
    if not dpy:
        return
    root = dpy.screen().root
    try:
        root.ungrab_key(X.AnyKey, X.AnyModifier)
        dpy.flush()
    except Exception:
        pass
    _state["grabbed"] = False


def _drain_events():
    dpy = _get_display()
    if not dpy:
        return
    try:
        while dpy.pending_events():
            dpy.next_event()
    except Exception:
        pass


def _apply_ewmh_hints(dpy, window_id: int):
    """Demande au WM de masquer la fenêtre de la barre des tâches/du pager et de la
    garder au premier plan (best-effort : dépend du support EWMH du WM en place)."""
    try:
        window = dpy.create_resource_object("window", window_id)
        root = dpy.screen().root

        def atom(name):
            return dpy.get_atom(name)

        for state_name in ("_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER", "_NET_WM_STATE_ABOVE"):
            ev = xevent.ClientMessage(
                window=window,
                client_type=atom("_NET_WM_STATE"),
                data=(32, [1, atom(state_name), 0, 0, 0])  # 1 = _NET_WM_STATE_ADD
            )
            root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)

        dpy.flush()
    except Exception:
        pass
