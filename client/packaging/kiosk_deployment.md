# Déploiement kiosque dédié (Windows / Linux)

Ces scripts implémentent le niveau "durcissement applicatif + déploiement OS dédié" :
un compte système restreint, connecté automatiquement, qui ne lance QUE l'app client
cybercafé — sans jamais exposer le bureau, la barre des tâches ou l'explorateur de
fichiers normal du poste.

Ils viennent en complément (pas en remplacement) du durcissement applicatif déjà
intégré dans le client (`platform_/windows.py`, `platform_/linux.py`,
`core/focus_guard.py`) : blocage des raccourcis d'évasion, masquage barre des
tâches, reprise de focus automatique.

## Linux — `linux_kiosk_setup.sh`

```bash
sudo ./linux_kiosk_setup.sh /opt/cybercafe-client
```

Crée un compte `kiosque` sans mot de passe utilisable en connexion classique,
configure l'autologin sur `tty1` (systemd), et démarre au login une session X
**sans aucun gestionnaire de fenêtres** qui ne lance que l'app cybercafé en plein
écran. Sans WM, il n'y a littéralement rien d'autre à atteindre (pas de panel, pas
de raccourcis WM qui entrent en conflit avec ceux que l'app tente de bloquer).

Prérequis sur le poste : `xorg-x11-server`/`xserver-xorg` + `xinit`, Python 3 et les
dépendances de `client/requirements.txt`.

## Windows — `windows_kiosk_setup.ps1`

```powershell
.\windows_kiosk_setup.ps1 -AppExePath "C:\CybercafeClient\cybercafe-client.exe" -KioskPassword "MotDePasseSolide!"
```

Crée un compte local standard (non admin) `kiosque`, configure l'autologin, et
remplace le **shell** de ce compte par l'app kiosque (`explorer.exe` — donc le
bureau, la barre des tâches, le menu Démarrer — ne se lance jamais pour ce compte).
Désactive aussi le Gestionnaire des tâches et les options gênantes de l'écran
Ctrl+Alt+Suppr pour ce compte.

⚠️ **Non testé sur une vraie machine Windows** (rédigé sans environnement Windows
disponible pendant le développement) — à valider sur un poste de test avant tout
déploiement en production.

⚠️ **Limite connue et acceptée** : `AutoAdminLogon` stocke `DefaultPassword` en
clair dans le registre (limitation native de Windows, pas de ce script). Pour un
déploiement plus soigné, remplacer cette étape par l'outil **Autologon** de
Sysinternals (Microsoft), qui chiffre le mot de passe via les secrets LSA au lieu
d'un registre en clair.

⚠️ Ctrl+Alt+Suppr lui-même ne peut jamais être intercepté par une application,
quelle qu'elle soit : c'est une protection du noyau Windows. Seules les *options*
présentées sur cet écran (verrouiller, changer d'utilisateur, Gestionnaire des
tâches) sont désactivables, ce que fait ce script.

## Après déploiement

Sur chaque poste, au premier démarrage dans le kiosque, l'assistant de
configuration du client (`SetupDialog`, voir `client/README.md`) demandera
l'adresse serveur, l'ID du poste et son token une seule fois ; ils sont ensuite
mémorisés dans le profil du compte kiosque.
