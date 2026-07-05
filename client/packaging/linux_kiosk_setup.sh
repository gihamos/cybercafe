#!/usr/bin/env bash
# Configure un poste Linux en kiosque dédié pour le client cybercafé :
# - compte système restreint dédié ("kiosque")
# - autologin sur tty1 (pas de gestionnaire de connexion graphique)
# - session X minimale (AUCUN gestionnaire de fenêtres) qui ne lance que l'app kiosque
#
# À exécuter en root sur le poste (une seule fois, à l'installation).
# Usage : sudo ./linux_kiosk_setup.sh /opt/cybercafe-client
#
# Après exécution : redémarrer le poste. Il doit démarrer directement dans l'app
# kiosque, sans bureau ni barre des tâches visible.

set -euo pipefail

APP_DIR="${1:-/opt/cybercafe-client}"
KIOSK_USER="kiosque"

if [ "$(id -u)" -ne 0 ]; then
    echo "Ce script doit être exécuté en root (sudo)." >&2
    exit 1
fi

if [ ! -d "$APP_DIR" ]; then
    echo "Dossier de l'app introuvable : $APP_DIR" >&2
    echo "Copiez d'abord le client (ou l'exécutable packagé) à cet endroit, ou passez le bon chemin en argument." >&2
    exit 1
fi

# 1. Compte dédié, sans droits admin, sans mot de passe utilisable en connexion classique
if ! id "$KIOSK_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$KIOSK_USER"
    usermod -L "$KIOSK_USER"   # verrouille le mot de passe : connexion uniquement via autologin
    echo "Utilisateur '$KIOSK_USER' créé."
else
    echo "Utilisateur '$KIOSK_USER' déjà existant, réutilisation."
fi

usermod -aG video,audio,plugdev "$KIOSK_USER" || true

# 2. Autologin sur tty1 (systemd)
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/override.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${KIOSK_USER} --noclear %I \$TERM
EOF
systemctl daemon-reload
systemctl enable getty@tty1.service

# 3. Lancement automatique de X (sans WM) au login sur tty1
KIOSK_HOME="$(getent passwd "$KIOSK_USER" | cut -d: -f6)"

cat > "$KIOSK_HOME/.xinitrc" <<EOF
#!/usr/bin/env bash
xset -dpms
xset s off
xset s noblank
exec python3 "$APP_DIR/main.py"
EOF
chmod +x "$KIOSK_HOME/.xinitrc"

cat >> "$KIOSK_HOME/.bash_profile" <<'EOF'

# Lance automatiquement la session kiosque au login sur tty1 uniquement
if [ -z "${DISPLAY:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx -- -nocursor
fi
EOF

chown -R "$KIOSK_USER:$KIOSK_USER" "$KIOSK_HOME/.xinitrc" "$KIOSK_HOME/.bash_profile"

echo
echo "Configuration terminée. Points à vérifier avant de redémarrer :"
echo "  - xorg-x11-server (ou xserver-xorg) et xinit sont installés"
echo "  - python3 + dépendances du client (requirements.txt) installées pour cet OS"
echo "  - $APP_DIR/config.py pointera vers ~/.config/cybercafe-client/config.json"
echo "    du compte '$KIOSK_USER' : lancez une fois l'app sous ce compte pour la"
echo "    première configuration (adresse serveur / poste_id / token), ou déposez"
echo "    directement le fichier config.json à cet emplacement."
echo
echo "Redémarrez le poste pour tester : il doit démarrer directement dans l'app kiosque."
