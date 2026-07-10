import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Lecture LOCALE du fichier d'historique du navigateur (pas d'interception réseau,
# pas de proxy) — voir la décision produit associée à cette fonctionnalité. Couvre les
# navigateurs Chromium (Chrome/Edge/Chromium, schéma SQLite identique) ; Firefox utilise
# un format différent et n'est pas géré pour l'instant.

_CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


def _chrome_time_to_datetime(chrome_time: int) -> datetime:
    return _CHROME_EPOCH + timedelta(microseconds=chrome_time)


def _chromium_profile_paths() -> list[tuple[str, Path]]:
    """[(nom_navigateur, chemin_vers_History), ...] pour les profils par défaut connus,
    selon l'OS — n'en vérifie pas l'existence ici, chaque chemin est best-effort."""
    home = Path.home()

    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return [
            ("chrome", local / "Google" / "Chrome" / "User Data" / "Default" / "History"),
            ("edge", local / "Microsoft" / "Edge" / "User Data" / "Default" / "History"),
        ]
    if sys.platform == "darwin":
        support = home / "Library" / "Application Support"
        return [
            ("chrome", support / "Google" / "Chrome" / "Default" / "History"),
            ("edge", support / "Microsoft Edge" / "Default" / "History"),
        ]
    return [
        ("chrome", home / ".config" / "google-chrome" / "Default" / "History"),
        ("chromium", home / ".config" / "chromium" / "Default" / "History"),
    ]


def _lire_profil(nom: str, chemin: Path, depuis: datetime) -> list[dict]:
    if not chemin.exists():
        return []

    # Le fichier est verrouillé tant que le navigateur tourne : on lit une copie.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp_path = tmp.name
        shutil.copy2(chemin, tmp_path)

        depuis_chrome = int((depuis - _CHROME_EPOCH).total_seconds() * 1_000_000)
        conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT url, title, last_visit_time FROM urls "
                "WHERE last_visit_time > ? ORDER BY last_visit_time ASC",
                (depuis_chrome,),
            ).fetchall()
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return []
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return [
        {
            "url": url,
            "titre": title,
            "date_visite": _chrome_time_to_datetime(last_visit_time).isoformat(),
            "navigateur": nom,
        }
        for url, title, last_visit_time in rows
        if url
    ]


def lire_historique_recent(depuis: datetime) -> list[dict]:
    """Lit les entrées visitées après `depuis` sur tous les navigateurs Chromium
    détectés. Best-effort : un navigateur absent ou un fichier illisible (verrouillé,
    corrompu...) est simplement ignoré plutôt que de faire échouer tout le cycle."""
    entrees: list[dict] = []
    for nom, chemin in _chromium_profile_paths():
        entrees.extend(_lire_profil(nom, chemin, depuis))
    return entrees
