from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.logger import logger


def _colonnes(conn, table: str) -> list[str]:
    return [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]


def _ajouter_colonnes(conn, table: str, colonnes: dict[str, str]) -> None:
    existantes = _colonnes(conn, table)
    if not existantes:
        return  # table pas encore créée : create_all s'en charge avec le schéma complet
    for nom, ddl in colonnes.items():
        if nom not in existantes:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {nom} {ddl}"))
            conn.commit()
            logger.info(f"Migration : colonne {table}.{nom} ajoutée")


def executer_migrations(engine: Engine) -> None:
    """Micro-migrations idempotentes pour les bases existantes : create_all ne crée
    que les tables manquantes, jamais les nouvelles colonnes — on les ajoute ici via
    ALTER TABLE ADD COLUMN (seule altération de schéma supportée par SQLite)."""
    with engine.connect() as conn:
        # Portail WiFi : fil de discussion par utilisateur (et non par poste).
        # user_id NULL = fil de poste classique ; renseigné = fil WiFi du client.
        _ajouter_colonnes(conn, "chat_messages", {
            "user_id": "INTEGER REFERENCES users(id)",
        })

        # Tickets : portée d'accès (poste fixe / wifi / les deux) + tickets crédit
        # (bons de recharge imprimables portant un montant).
        _ajouter_colonnes(conn, "tickets", {
            "acces": "VARCHAR DEFAULT 'les_deux'",
            "credit_euros": "FLOAT",
        })

        # Articles : code-barres, périssabilité et fiche produit détaillée.
        _ajouter_colonnes(conn, "articles", {
            "code_barre": "VARCHAR",
            "date_peremption": "DATE",
            "origine": "VARCHAR",
            "ingredients": "VARCHAR",
            "poids_grammes": "FLOAT",
            "allergenes": "VARCHAR",
        })

        # Suivi de commande (achat → récupération) des ventes d'articles.
        _ajouter_colonnes(conn, "achats_articles", {
            "statut_commande": "VARCHAR DEFAULT 'recuperee'",
        })

        # Images de catégories d'articles (à la place des emoji).
        _ajouter_colonnes(conn, "article_categories", {
            "image_cle_stockage": "VARCHAR",
            "image_content_type": "VARCHAR",
        })

        # Charte d'utilisation : date d'acceptation par le client.
        _ajouter_colonnes(conn, "users", {
            "charte_acceptee_le": "DATETIME",
        })

        # Impressions : indicateur de règlement (permet l'exécution côté admin
        # et le lancement automatique quand le solde du client suffit).
        _ajouter_colonnes(conn, "impressions", {
            "paye": "BOOLEAN DEFAULT 0",
        })

        # Caisse pro : code unique d'identification (SKU) et type de conservation
        # (non périssable / périssable / frais) des produits.
        _ajouter_colonnes(conn, "articles", {
            "sku": "VARCHAR",
            "type_conservation": "VARCHAR DEFAULT 'non_perissable'",
        })
        _ajouter_colonnes(conn, "tickets", {
            "user_id": "INTEGER REFERENCES users(id)",
        })

        # Contrôle réseau réel : identifiant réseau du client de la session (IP/MAC)
        # et indicateur d'autorisation active côté routeur.
        _ajouter_colonnes(conn, "sessions", {
            "ip_client": "VARCHAR",
            "mac_client": "VARCHAR",
            "acces_reseau_actif": "BOOLEAN DEFAULT 0",
        })

        # Limite de sessions actives simultanées (compte / offre / ticket) — NULL =
        # illimité à chaque niveau. Voir services/portail_service.py::verifier_limite_sessions.
        _ajouter_colonnes(conn, "users", {
            "max_sessions_simultanees": "INTEGER",
        })
        _ajouter_colonnes(conn, "offre", {
            "max_sessions_simultanees": "INTEGER",
        })
        _ajouter_colonnes(conn, "tickets", {
            "max_sessions_simultanees": "INTEGER",
        })

        # Chat mode ticket (anonyme) : fil par session plutôt que par utilisateur,
        # éphémère sauf conservation explicite par un opérateur.
        _ajouter_colonnes(conn, "chat_messages", {
            "session_id": "INTEGER REFERENCES sessions(id)",
            "conserver": "BOOLEAN DEFAULT 0",
        })
