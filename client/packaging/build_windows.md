# Build Windows (PyInstaller)

⚠️ Non testé en conditions réelles (pas de machine Windows disponible pendant le
développement) — les commandes suivent exactement le même principe que le build
Linux (déjà testé et fonctionnel), qui utilise le même fichier spec. À valider sur
un poste Windows avant déploiement.

```powershell
cd client
pip install -r requirements.txt
pip install pyinstaller
pyinstaller packaging\cybercafe-client.spec
```

L'exécutable est généré dans `client\dist\cybercafe-client.exe` (autonome, aucune
dépendance Python à installer sur le poste cible).

Copier cet `.exe` sur le poste (ex: `C:\CybercafeClient\cybercafe-client.exe`), puis
suivre `kiosk_deployment.md` pour configurer le compte kiosque dédié
(`windows_kiosk_setup.ps1` a justement besoin du chemin vers cet `.exe`).

## Icône (optionnel)

Pour ajouter une icône à l'exécutable, placer un fichier `.ico` dans ce dossier
(ex: `icon.ico`) et décommenter/adapter la ligne `icon=...` dans
`cybercafe-client.spec`.

## Notes

- `console=False` dans le spec masque la fenêtre console — les erreurs ne
  s'afficheront pas dans un terminal ; pour déboguer un premier build, repasser
  temporairement `console=True` dans le spec.
- Le hook clavier bas niveau (`platform_/windows.py`) et le masquage de la barre
  des tâches nécessitent d'exécuter l'app dans une session utilisateur normale
  (pas de contrainte de packaging particulière), mais sont sans effet avant que
  `LockScreen.show_kiosk()` ne soit appelé.
