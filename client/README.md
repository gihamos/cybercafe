# Client desktop cybercafé (poste)

Application PySide6 (Windows + Linux) installée sur chaque poste client du cybercafé.
Se connecte au serveur en WebSocket, affiche un écran de verrouillage kiosk tant qu'aucune
session n'est active, et un overlay (temps/data restant, boutique, impression) pendant la
session.

## Installation (dev)

```bash
cd client
pip install -r requirements.txt
python main.py
```

## Première configuration

Au premier lancement, l'app demande :
- **Adresse du serveur** (ex: `192.168.1.10:8000`, sans `http://`)
- **ID du poste** et **token** — générés côté serveur à la création du poste
  (`POST /poste/` en tant qu'admin, le token n'est renvoyé qu'à ce moment-là ;
  utiliser `POST /poste/{id}/regenerer-token` s'il a été perdu).

Ces informations sont enregistrées dans :
- Linux : `~/.config/cybercafe-client/config.json`
- Windows : `%APPDATA%\cybercafe-client\config.json`

## Fonctionnalités

- Connexion WebSocket authentifiée par token, heartbeat périodique, passage en
  ligne/hors ligne côté serveur.
- Écran de verrouillage kiosk (login ou ticket), démarrage/fin de session réelle
  côté serveur, overlay temps/data restant.
- Réaction en temps réel aux actions déclenchées côté serveur (opérateur qui
  démarre/termine une session, verrouille le poste, envoie un message, met à jour
  la liste des applications bloquées...).
- Boutique d'articles (achat débité du solde du client connecté) et impression
  locale (spouleur du poste) avec facturation automatique côté serveur.
- Blocage d'applications à distance : le serveur pousse une liste de noms de
  processus à bloquer, le client les termine en continu (`core/process_guard.py`).
- Durcissement kiosk applicatif multiplateforme (`platform_/`) : blocage des
  raccourcis d'évasion (Alt+Tab, touche Windows, Alt+F4, Ctrl+Échap), masquage de
  la barre des tâches, reprise automatique du focus — actif uniquement quand
  l'écran de verrouillage est affiché (pas pendant une session active).

## Mode kiosk : deux niveaux

1. **Durcissement applicatif** (`platform_/`, `core/focus_guard.py`) : actif dès
   que l'app tourne, sur une session utilisateur normale, aucune reconfiguration
   du poste nécessaire. Limite connue : Ctrl+Alt+Suppr ne peut être intercepté par
   aucune application (protection noyau).
2. **Déploiement OS dédié** (`packaging/kiosk_deployment.md`) : compte système
   restreint en autologin qui ne lance QUE l'app kiosque (shell de remplacement sur
   Windows, session X sans gestionnaire de fenêtres sur Linux) — le bureau normal,
   la barre des tâches et l'explorateur de fichiers ne sont jamais accessibles.
   C'est le niveau recommandé pour un vrai poste de production.

## Packaging

Voir `packaging/build_linux.md` et `packaging/build_windows.md` (PyInstaller,
spec partagée `packaging/cybercafe-client.spec`). Le build Linux a été testé avec
succès dans cet environnement ; le build Windows suit le même principe mais n'a
pas pu être vérifié faute de machine Windows disponible.
