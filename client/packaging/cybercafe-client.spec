# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller pour le client cybercafé (Windows + Linux).
# Build : depuis le dossier client/, lancer `pyinstaller packaging/cybercafe-client.spec`
import sys
from pathlib import Path

block_cipher = None
client_dir = Path(SPECPATH).parent

hidden_imports = ["websockets", "psutil", "pypdf"]
if sys.platform.startswith("linux"):
    hidden_imports += ["Xlib", "Xlib.ext"]

a = Analysis(
    [str(client_dir / "main.py")],
    pathex=[str(client_dir)],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="cybercafe-client",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # pas de console (app graphique)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # ex: str(client_dir / "packaging" / "icon.ico") sous Windows
)
