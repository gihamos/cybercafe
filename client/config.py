import json
import os
import sys
from pathlib import Path


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home()))
        return Path(base) / "cybercafe-client"
    return Path.home() / ".config" / "cybercafe-client"


CONFIG_PATH = _config_dir() / "config.json"

DEFAULT_CONFIG = {
    "server_url": "",   # ex: 192.168.1.10:8000 (sans schéma)
    "poste_id": None,
    "token": None,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)

    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def is_configured(config: dict) -> bool:
    return bool(config.get("server_url") and config.get("poste_id") and config.get("token"))
