# Cybercafé — Serveur

API centrale du système de gestion de cybercafé. Expose une API REST et deux canaux
WebSocket (postes clients et panneau d'administration), porte toute la logique métier
et la base de données. Les deux autres modules ([`client/`](../client/README.md) et
[`administration/`](../administration/README.md)) ne sont que des consommateurs de
cette API — aucune logique métier n'existe côté client ou admin.

## Stack

- **FastAPI** + **Uvicorn** — API HTTP et WebSocket
- **SQLAlchemy** (ORM) — SQLite par défaut, compatible tout backend supporté par
  SQLAlchemy via `DATABASE_URL`
- **PyJWT** — authentification par jeton, **pwdlib[argon2]** — hachage des mots de passe
- **httpx** — appels sortants vers les passerelles de paiement externes

## Installation

```bash
cd server
python -m venv .venv
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Au premier démarrage, le serveur crée la base SQLite (`data/cybercafe.db`) et un
compte administrateur (identifiants par défaut `admin123` / `admin123`, à changer via
les variables d'environnement `ADMINUSERNAME`/`ADMINPASSWORD` en production).

La documentation interactive de l'API est disponible sur `/docs` (Swagger) et
`/redoc` une fois le serveur lancé.

## Variables d'environnement

Toutes optionnelles avec une valeur par défaut adaptée au développement local. À
définir dans un fichier `.env` à la racine de `server/` (voir `params.py` pour la
liste exhaustive) :

| Variable | Rôle | Défaut |
|---|---|---|
| `DATABASE_URL` | URL de connexion SQLAlchemy | `sqlite:///./data/cybercafe.db` |
| `JWT_SECRET` | Secret de signature des jetons — **à changer en production** | valeur de dev codée en dur |
| `ADMINUSERNAME`, `ADMINPASSWORD`, `ADMINEMAIL`, `ADMINFIRSTNAME` | Compte admin créé au premier démarrage | `admin123` / `admin123` / ... |
| `CORS_ORIGINS` | Origines autorisées (liste séparée par des virgules) | `http://localhost:5173,http://127.0.0.1:5173` |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE`, `PAYPAL_WEBHOOK_ID` | Passerelle PayPal (paiement en ligne) | vide / `sandbox` |
| `PAYMENT_RETURN_URL`, `PAYMENT_CANCEL_URL` | Redirections post-paiement PayPal vers l'admin | `http://localhost:5173/paiement/...` |
| `STORAGE_PROVIDER` | Fournisseur de stockage fichiers (`local` ou `s3`) | `local` |
| `STORAGE_LOCAL_PATH` | Répertoire de stockage si `local` | `data/stockage` |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Fournisseur S3/MinIO (nécessite `boto3`) | vide |
| `CARTE_API_BASE`, `CARTE_API_KEY` | Passerelle carte bancaire en caisse | URL d'exemple |
| `MOBILE_MONEY_API_BASE`, `MOBILE_MONEY_API_KEY` | Passerelle mobile money en caisse | URL d'exemple |

Les passerelles carte/mobile money et PayPal sont livrées avec une intégration
complète (structure de requêtes, gestion des erreurs, remboursement) mais **non
testées contre de vrais identifiants fournisseur** — voir plus bas.

## Architecture

```
server/
├── main.py            Point d'entrée FastAPI, montage des routers, CORS, admin bootstrap
├── params.py           Configuration (variables d'environnement)
├── config/              Connexion base de données (engine, session, Base)
├── models/               Tables SQLAlchemy (un fichier par entité)
├── schemas/               Schémas Pydantic (validation d'entrée/sortie)
├── services/               Logique métier — AUCUNE logique métier dans les routers
├── router/                 Endpoints FastAPI — décodent la requête, appellent un service
├── dependencies/            Auth JWT (auth.py) et contrôle d'accès (access.py : rôles + permissions)
├── websocket/                Gestionnaire de connexions WebSocket (postes + admins)
├── utils/                     Sécurité, logger, générateur de code, Wake-on-LAN
├── validators/                 Validateurs de requête partagés
└── data/                       Base SQLite + fichiers stockés (créé au démarrage, ignoré par git)
```

Chaque domaine suit la même couche : `models/` → `services/` → `router/`. Les
providers pluggables (paiement, stockage, promotions) suivent tous le même patron :
une classe abstraite dans `base.py`, une implémentation par fournisseur, un registre
dans `__init__.py` — ajouter un fournisseur ne touche à rien d'autre.

```
services/payment_gateway/      Paiement en ligne redirigé (PayPal)
services/in_person_gateway/     Paiement en caisse synchrone (carte, mobile money)
services/storage_provider/       Stockage de fichiers (local, S3/MinIO)
services/promotion_mechanisms/    Mécanismes de promotion (pourcentage, montant fixe, happy hour)
```

## Authentification et permissions

- **JWT** via `POST /auth/login` (username + password en query params), rafraîchi
  par `GET /auth/refreshToken`.
- Trois rôles : `admin`, `operateur`, `client`.
- **Permissions granulaires par opérateur** (`User.permissions`, `NULL` = accès
  complet par défaut) sur les modules caisse, chat, postes, catalogue, clients,
  bande passante et surveillance — voir `services/permission_service.py` et la
  dépendance `require_permission()`. Les admins ont toujours accès à tout.
- Les postes kiosque n'ont pas de JWT : ils s'authentifient par un **token dédié**
  généré à leur création (`POST /poste/`), utilisé sur le WebSocket
  (`/ws/poste/{id}?token=...`) et sur les endpoints REST poste-à-poste
  (`*_poste.py`, ex. `stockage_poste.py`, `chat_poste.py`, `surveillance_poste.py`).

## WebSocket

| Endpoint | Utilisé par | Rôle |
|---|---|---|
| `/ws/poste/{poste_id}?token=...` | `client/` | Canal temps réel du poste : pairage, sessions, chat, blocage d'apps/sites, Pay & Connect |
| `/ws/admin?token=<jwt>` | `administration/` | Diffusion temps réel vers les admins connectés : état des postes, sessions, chat |

## Domaines fonctionnels (routers)

| Domaine | Router | Détail |
|---|---|---|
| Auth | `auth` | Connexion, rafraîchissement de jeton |
| Comptes | `user`, `user_group` | CRUD comptes, équipe, permissions, groupes multi-appartenance |
| Postes | `poste`, `ws_poste` | Cycle de vie poste, verrouillage, commandes, WoL |
| Sessions | `session` | Sessions de connexion (temps/data) |
| Catalogue | `offre`, `article`, `article_categorie`, `tickets`, `promotion` | Forfaits, articles + stock, tickets prépayés, promotions cumulables |
| Paiements | `paiement`, `paiement_en_ligne`, `caisse`, `pay_connect` | Encaissement, remboursement, session de caisse, paiement en ligne redirigé, accès instantané payé |
| Réseau & contenu | `bande_passante`, `site_regle`, `app_bloquee` | Profils de bande passante, filtrage de sites (liste noire/blanche + âge), blocage d'applications |
| Communication | `chat`, `chat_poste` | Chat opérateur ↔ poste avec pièces jointes |
| Stockage | `stockage`, `stockage_poste` | Espace fichiers par compte/ticket, avec quota |
| Surveillance | `surveillance`, `surveillance_poste` | Captures d'écran + historique de navigation périodiques |
| Suivi | `impression`, `notification`, `historique`, `stats` | Facturation d'impression, notifications, journal d'audit, statistiques |
| Configuration | `config`, `system_setting` | Réglages généraux du cybercafé (nom, logo, devise...) et paramètres système bruts |

## Base de données

SQLite en développement (fichier unique, aucune installation requise), créée
automatiquement via `Base.metadata.create_all()` au démarrage — **pas de système de
migration formel** (Alembic ou équivalent) à ce stade : tout changement de schéma
nécessite de supprimer `data/cybercafe.db` en dev, ou d'écrire la migration à la main
en production. Compatible tout autre moteur supporté par SQLAlchemy via
`DATABASE_URL` (PostgreSQL, MySQL...).

## Notes sur les passerelles de paiement

`services/in_person_gateway/` (carte, mobile money) et `services/payment_gateway/`
(PayPal) sont structurellement complets — requêtes HTTP, gestion des échecs,
remboursement — mais n'ont été vérifiés qu'en **mode échec propre** (sans identifiants
réels : le serveur renvoie une erreur 400 lisible plutôt qu'un crash). Avant mise en
production, tester chaque passerelle avec de vrais identifiants sandbox fournisseur.
