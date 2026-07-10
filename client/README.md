# Cybercafé — Client (poste kiosque)

Application PySide6 (Windows + Linux) installée sur chaque poste client du cybercafé.
Se connecte au [serveur](../server/README.md) en WebSocket, affiche un écran de
verrouillage kiosque tant qu'aucune session n'est active, et un overlay (temps/data
restant, boutique, chat, stockage, impression) pendant la session. Aucune logique
métier ici : toute décision (tarifs, quotas, droits) vient du serveur.

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

**Session**
- Connexion WebSocket authentifiée par token, heartbeat périodique, passage en
  ligne/hors ligne côté serveur.
- Écran de verrouillage kiosque (identifiants ou ticket), démarrage/fin de session
  réelle côté serveur, overlay temps/data restant.
- « Pay & Connect » : accès instantané payé sur place (solde ou espèces avec
  confirmation opérateur), sans création de compte préalable.
- Réaction en temps réel aux actions déclenchées côté serveur (opérateur qui
  démarre/termine une session, verrouille le poste, envoie un message, met à jour
  la liste des applications ou sites bloqués...).

**Achats & impression**
- Boutique d'articles (achat débité du solde du client connecté) et impression
  locale (spouleur du poste) avec facturation automatique côté serveur.

**Chat & stockage**
- Discussion en direct avec l'opérateur, historique persistant renvoyé à chaque
  reconnexion, **pièces jointes** dans les deux sens (taille max configurable côté
  admin) — transfert par requête HTTP classique, pas par le canal WebSocket.
- Espace de stockage réseau personnel : upload/téléchargement/suppression de
  fichiers, avec quota affiché. Lié au compte du client s'il est connecté, ou
  temporaire et purgé automatiquement en fin de session s'il s'agit d'un ticket
  anonyme.

**Restrictions**
- Blocage d'applications à distance : le serveur pousse une liste de noms de
  processus à bloquer, le client les termine en continu (`core/process_guard.py`).
- Blocage de sites par réécriture du fichier hosts, poussé par le serveur à chaque
  pairage/démarrage/changement de session (`core/hosts_manager.py`).
- Durcissement kiosque applicatif multiplateforme (`platform_/`) : blocage des
  raccourcis d'évasion (Alt+Tab, touche Windows, Alt+F4, Ctrl+Échap), masquage de
  la barre des tâches, reprise automatique du focus — actif uniquement quand
  l'écran de verrouillage est affiché (pas pendant une session active).

**Surveillance** *(activée par défaut, désactivable côté configuration serveur)*
- Capture d'écran périodique du poste pendant une session active, envoyée au
  serveur (`core/screenshot_capturer.py`).
- Lecture **locale** de l'historique du navigateur (Chrome/Chromium/Edge — copie
  du fichier `History` SQLite pour contourner le verrou du navigateur en cours
  d'exécution) et envoi périodique des nouvelles entrées depuis le début de la
  session (`core/browser_history_reader.py`).
- **Aucune interception réseau ni proxy** : uniquement des captures d'écran et une
  lecture de fichier local, strictement pendant une session active — jamais sur
  l'écran de verrouillage. L'intervalle et l'activation de chaque flux sont
  configurables depuis le panneau d'administration (Paramètres).

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

## Architecture

```
client/
├── main.py                  Point d'entrée, assemblage de l'app (PosteClientApp)
├── config.py                  Chargement/sauvegarde de la config locale
├── core/                        Logique non-UI : clients REST, WebSocket, gardes système
│   ├── ws_client.py               Canal WebSocket principal (sessions, chat texte, achats...)
│   ├── storage_client.py           Client REST de l'espace de stockage réseau
│   ├── chat_client.py               Client REST des pièces jointes du chat
│   ├── surveillance_client.py        Client REST des captures d'écran + historique
│   ├── screenshot_capturer.py         Capture d'écran (Qt)
│   ├── browser_history_reader.py       Lecture locale de l'historique navigateur
│   ├── process_guard.py                 Blocage d'applications
│   ├── hosts_manager.py                  Blocage de sites (fichier hosts)
│   └── focus_guard.py                     Durcissement kiosque (focus, raccourcis)
├── ui/                          Fenêtres/dialogues PySide6 (écran de verrouillage, overlay, boutique...)
├── platform_/                     Implémentations spécifiques Windows/Linux du durcissement kiosque
└── packaging/                       Scripts et notes de build (PyInstaller) + guide de déploiement kiosque
```

Les flux volumineux ou binaires (stockage, pièces jointes de chat, captures d'écran,
historique de navigation) passent par des requêtes HTTP classiques authentifiées par
le token du poste — le WebSocket ne sert qu'aux échanges courts et à la diffusion
d'événements en temps réel.

## Packaging

Voir `packaging/build_linux.md` et `packaging/build_windows.md` (PyInstaller,
spec partagée `packaging/cybercafe-client.spec`). Le build Linux a été testé avec
succès dans cet environnement ; le build Windows suit le même principe mais n'a
pas pu être vérifié faute de machine Windows disponible.
