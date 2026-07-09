"""Blocage de sites web par domaine via le fichier hosts du système — même principe
que le blocage de processus (process_guard.py) mais pour la navigation : le domaine
bloqué est redirigé vers 127.0.0.1, ce qui fonctionne avec n'importe quel navigateur
sans configuration supplémentaire côté client.

Nécessite que le client tourne avec des droits administrateur/root (déjà requis pour
le reste du durcissement kiosk — voir packaging/). Si l'écriture échoue (droits
insuffisants), la fonction échoue silencieusement : le filtrage de contenu est une
fonctionnalité annexe, elle ne doit jamais faire planter le poste."""

import os
import sys
from pathlib import Path

MARKER_START = "# === CYBERCAFE-BLOCKED-SITES-START ==="
MARKER_END = "# === CYBERCAFE-BLOCKED-SITES-END ==="


def _hosts_path() -> Path:
    if sys.platform == "win32":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        return Path(system_root) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def apply_blocked_domains(domaines: list[str]) -> bool:
    """Réécrit le bloc de domaines bloqués géré par l'application dans le fichier
    hosts, en préservant tout le reste du fichier (règles système, autres entrées
    manuelles). Idempotent : peut être appelé à chaque changement de session."""
    path = _hosts_path()

    try:
        original = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return False

    lines = original.splitlines()
    if MARKER_START in lines and MARKER_END in lines:
        start = lines.index(MARKER_START)
        end = lines.index(MARKER_END)
        lines = lines[:start] + lines[end + 1:]
    while lines and lines[-1].strip() == "":
        lines.pop()

    if domaines:
        bloc = [MARKER_START]
        for domaine in sorted(set(domaines)):
            bloc.append(f"127.0.0.1 {domaine}")
            if not domaine.startswith("www."):
                bloc.append(f"127.0.0.1 www.{domaine}")
        bloc.append(MARKER_END)
        lines = lines + [""] + bloc

    try:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        return False

    return True
