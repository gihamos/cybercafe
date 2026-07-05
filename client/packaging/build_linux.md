# Build Linux (PyInstaller)

Testé dans cet environnement de développement (build + démarrage vérifiés).

```bash
cd client
pip install -r requirements.txt
pip install pyinstaller
pyinstaller packaging/cybercafe-client.spec
```

L'exécutable autonome est généré dans `client/dist/cybercafe-client` (un seul
fichier, aucune dépendance Python à installer sur le poste cible).

Copier cet exécutable sur le poste (ex: `/opt/cybercafe-client/cybercafe-client`),
puis suivre `kiosk_deployment.md` pour le déploiement en kiosque dédié (ou lancer
l'exécutable directement pour un usage plus simple, sans durcissement OS).

## Dépendances système requises sur le poste cible

- Un serveur X11 (le durcissement kiosk et l'affichage nécessitent X ; Wayland pur
  n'est pas supporté pour l'instant, voir `platform_/linux.py`)
- Bibliothèques Qt standards (généralement déjà présentes sur toute distribution
  avec un environnement graphique)
- CUPS configuré avec une imprimante par défaut si l'impression est utilisée
  (`lp` doit fonctionner en ligne de commande)

## Warnings de build à ignorer

PyInstaller peut afficher des avertissements du type :
```
Library not found: could not resolve 'libtiff.so.5' / 'libxcb-cursor.so.0'
```
Ce sont des dépendances de plugins Qt optionnels (formats d'image rares, thèmes
d'icônes) non utilisés par cette application : sans conséquence.
