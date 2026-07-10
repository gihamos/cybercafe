# Cybercafé — Système de gestion

Système complet de gestion de cybercafé : postes clients en kiosque, serveur central
et panneau d'administration web. Conçu pour un opérateur qui gère l'accueil, la
caisse, le catalogue (forfaits/articles/tickets), la surveillance des postes et les
accès de son équipe depuis une seule interface, pendant que chaque poste client tourne
en mode kiosque verrouillé.

## Architecture

Le projet est composé de **trois modules strictement indépendants**, qui ne
communiquent qu'à travers l'API HTTP/WebSocket du serveur — jamais par import direct
de code entre eux :

```
┌───────────────────────┐                          ┌───────────────────────┐
│ client/                │                          │                       │
│ Poste kiosque (PySide6)│ ◄── HTTP + WebSocket ──► │ server/               │
└───────────────────────┘                          │ API centrale (FastAPI)│
                                                     │ + base de données     │
┌───────────────────────┐                          │                       │
│ administration/        │ ◄── HTTP + WebSocket ──► │                       │
│ Panneau web (React)    │                          └───────────────────────┘
└───────────────────────┘
```

| Module | Rôle | Stack |
|---|---|---|
| [`server/`](server/README.md) | API centrale, base de données, logique métier, WebSocket temps réel | FastAPI, SQLAlchemy, SQLite |
| [`client/`](client/README.md) | Application kiosque installée sur chaque poste client | PySide6 (Python) |
| [`administration/`](administration/README.md) | Panneau web pour l'exploitant et son équipe | React 19, TypeScript, Vite |

Chaque module a son propre README avec les détails d'installation, de configuration
et d'architecture interne — celui-ci ne donne qu'une vue d'ensemble.

## Fonctionnalités

**Postes & sessions**
- Écran de verrouillage kiosque, démarrage de session par identifiants ou ticket,
  suivi temps/data en direct, fin automatique à expiration.
- Verrouillage/déverrouillage à distance, commandes, réveil réseau (Wake-on-LAN),
  détection hors-ligne, grille de supervision temps réel côté admin.
- Durcissement kiosque applicatif (blocage des raccourcis d'évasion) + guide de
  déploiement en compte système restreint pour un vrai poste de production.

**Clients & accès**
- Comptes clients avec pièce d'identité, notes, âge (utilisé pour les règles de
  filtrage), solde rechargeable, historique complet (achats, abonnements, paiements,
  sessions).
- Appartenance à **plusieurs groupes simultanément**, chaque groupe portant ses
  propres limites de bande passante, quota de stockage et règles de filtrage de
  contenu (liste noire/blanche, avec seuils d'âge) — fusionnées par la règle la plus
  restrictive.

**Catalogue & caisse**
- Offres (temps/data/illimité), articles avec suivi de stock et alerte de
  réapprovisionnement, promotions cumulables (automatiques + code), tickets prépayés
  générés et imprimables en lot, avec suivi individuel de leur consommation.
- Caisse avec ouverture/clôture, ventilation par moyen de paiement, encaissement
  direct (recharge de solde, vente hors catalogue), remboursements.
- Paiements espèces/virement/carte/mobile money/PayPal — carte et mobile money
  passent par une passerelle fournisseur pluggable (validation + remboursement),
  PayPal en paiement en ligne redirigé.
- « Pay & Connect » : session instantanée payée sur place sans création de compte.

**Communication & surveillance**
- Chat en direct opérateur ↔ poste, persistant, avec pièces jointes (taille
  configurable).
- Captures d'écran périodiques et lecture locale de l'historique de navigation
  pendant les sessions actives (aucune interception réseau) — consultables depuis le
  panneau d'administration.

**Administration**
- Rôles admin/opérateur avec système de permissions granulaires par module
  (caisse, chat, postes, catalogue, clients, bande passante, surveillance) — chaque
  opérateur peut aussi modifier son propre compte.
- Statistiques (revenus, occupation, ventes), historique d'audit filtrable,
  configuration générale du cybercafé (nom, logo, adresse, SIRET, devise).

## Démarrage rapide (développement)

Les trois modules se lancent indépendamment. Dans trois terminaux :

```bash
# 1. Serveur (voir server/README.md pour les variables d'environnement)
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. Panneau d'administration
cd administration
npm install
npm run dev

# 3. Client kiosque (sur le poste, une fois un poste créé côté admin)
cd client
pip install -r requirements.txt
python main.py
```

Consultez le README de chaque module pour la configuration détaillée (variables
d'environnement, première connexion du client, build de production).

## Structure du dépôt

```
cybercafe/
├── server/            API FastAPI — voir server/README.md
├── client/            Application kiosque PySide6 — voir client/README.md
└── administration/    Panneau web React — voir administration/README.md
```
