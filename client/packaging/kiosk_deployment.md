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

## Niveau de privilège requis (commandes système à distance)

Les commandes système déclenchées depuis l'administration (`core/system_commands.py`
— redémarrage, extinction, verrouillage de lecteur) ont des besoins différents
selon leur nature ; **aucune n'exige un accès administrateur généralisé** :

- **Redémarrer / éteindre** (`shutdown /r`, `/s` sur Windows ; `systemctl reboot`/
  `poweroff` sur Linux) : fonctionne avec le compte `kiosque` **standard** créé
  par ces scripts — `SE_SHUTDOWN_NAME` est accordé par défaut aux utilisateurs
  standards sur un poste de travail Windows, et `systemctl` autorise reboot/
  poweroff aux sessions actives par polkit par défaut sur la plupart des
  distributions desktop. Rien à changer dans le déploiement actuel.
- **Verrouiller/déverrouiller un lecteur** : implémenté aujourd'hui via la
  stratégie `NoDrives` en **HKCU** (registre par utilisateur, pas HKLM) sur
  Windows — fonctionne aussi avec le compte `kiosque` standard, sans élévation.
  ⚠️ Cette implémentation ne masque le lecteur que dans les API shell
  (explorateur, boîtes de dialogue ouvrir/enregistrer d'autres applications) —
  elle ne bloque **pas** un accès en ligne de commande ou par une application
  qui contourne le shell. Un blocage réel au niveau pilote/matériel (ex:
  stratégie de groupe "Removable Storage Access", ou désactivation du pilote de
  stockage de masse USB) nécessiterait HKLM et donc un contexte administrateur
  — pas implémenté ici, à traiter si le besoin de blocage réel (pas seulement
  visuel) se confirme.

Sur Linux, le verrouillage de lecteur (`umount` du point de montage) fonctionne
avec les droits du compte `kiosque` sur les points de montage qu'il possède
(montage utilisateur via udisks2) ; **aucune règle sudo/polkit supplémentaire
n'est nécessaire** pour cette seule capacité. Un blocage *persistant* (empêcher
un remontage automatique) est une politique continue distincte — voir l'étape
"contrôle des disques/lecteurs" à venir, qui nécessitera là une règle polkit
dédiée (jamais un accès sudo généraliste).
