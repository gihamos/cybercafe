# Cybercafé — Panneau d'administration

Panneau web pour l'exploitant du cybercafé et son équipe : supervision des postes en
temps réel, caisse, catalogue, clients, chat, surveillance, statistiques et
configuration générale. Consomme exclusivement l'API du [`server/`](../server/README.md)
— aucune logique métier n'est dupliquée ici.

## Stack

- **React 19** + **TypeScript** + **Vite 8**
- **react-router-dom** — routage
- **lucide-react** — icônes
- Pas de librairie de state management externe : état local par page + un contexte
  d'authentification global (`src/auth/AuthContext.tsx`)
- Design system maison en CSS custom properties (`src/index.css`), thème clair/sombre

## Installation

```bash
cd administration
npm install
cp .env.example .env      # ajuster VITE_API_BASE_URL si le serveur n'est pas en local
npm run dev
```

Le serveur doit tourner et autoriser l'origine du panneau via `CORS_ORIGINS` côté
serveur (`http://localhost:5173` par défaut, déjà autorisé de base).

## Scripts

| Commande | Effet |
|---|---|
| `npm run dev` | Serveur de développement Vite avec rechargement à chaud |
| `npm run build` | **`tsc -b` puis `vite build`** — le typecheck fait partie du build (voir note ci-dessous) |
| `npm run preview` | Sert le build de production en local |
| `npm run lint` | Lint via Oxlint |

> **Note typecheck** : le `tsconfig.json` racine n'a pas de `files`, seulement des
> `references` — un simple `npx tsc --noEmit` ne vérifie donc rien. Utiliser
> `npx tsc -b --noEmit` (mode build, ce que fait `npm run build`) pour un vrai
> typecheck.

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `VITE_API_BASE_URL` | URL de base de l'API serveur | `http://127.0.0.1:8000` |

## Authentification

Connexion via `POST /auth/login`, jeton JWT stocké en `localStorage` et décodé
côté client pour peupler `AuthContext` (id, username, email, rôle) — pas d'appel
serveur supplémentaire tant que le jeton est valide. Un événement
`cybercafe:unauthorized`, émis par le client API sur toute réponse 401, déconnecte
automatiquement l'utilisateur.

Les éléments de navigation et certaines routes sont conditionnés :
- au **rôle** (`admin` uniquement pour Équipe et Paramètres) ;
- aux **permissions** de l'opérateur (`GET /user/me/permissions`), pour les modules
  restreignables (ex. Surveillance) — un opérateur sans permission explicite garde
  l'accès complet par défaut (`permissions: null`).

## Structure

```
src/
├── api/               Client HTTP (client.ts), types miroir des schémas serveur (types.ts)
├── auth/                Contexte d'authentification, page de connexion
├── ws/                   Hook WebSocket admin (useAdminSocket) — état temps réel des postes
├── layout/                AppLayout : barre latérale, navigation groupée, thème, badges temps réel
├── components/             Composants partagés entre pages (ex. MonCompteModal)
├── pages/                   Une page par domaine fonctionnel (voir tableau ci-dessous)
├── utils/                    Impression de reçus/tickets (receipt.ts)
└── index.css                  Design system : variables de thème clair/sombre, composants (cartes, badges, tables...)
```

## Pages

| Groupe de navigation | Pages |
|---|---|
| Vue d'ensemble | Tableau de bord, Statistiques |
| Exploitation | Postes (grille temps réel), Surveillance, Chat, Pay & Connect, Caisse |
| Clients | Clients, Groupes, Équipe *(admin)* |
| Catalogue & finances | Offres, Tickets, Articles, Promotions, Paiements, Stockage |
| Système | Impression, Bande passante, Historique, Paramètres *(admin)* |

Chaque page suit le même patron : chargement via `api.get<T>(...)`, formulaires en
modale (`.modal-overlay` / `.modal`), erreurs affichées inline plutôt qu'en `alert()`
sauf pour les actions ponctuelles simples.

## Temps réel

`useAdminSocket` ouvre `/ws/admin?token=<jwt>` et diffuse les événements serveur
(changement d'état d'un poste, session démarrée/terminée, nouveau message de chat...)
à toutes les pages qui s'y abonnent — la grille des postes et le chat se mettent à
jour sans rechargement.

## Design system

Toutes les couleurs passent par des variables CSS (`--bg`, `--surface`, `--text`,
`--accent`, palette de statut `--good`/`--warning`/`--serious`/`--critical`...)
définies pour le thème clair par défaut et surchargées sous
`@media (prefers-color-scheme: dark)` ainsi que `:root[data-theme="dark"]` pour le
bouton de bascule manuelle. Ne jamais coder une couleur en dur dans une page — passer
par les variables existantes ou en ajouter une dans `index.css`.
