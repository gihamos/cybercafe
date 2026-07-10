from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.paiement import Paiement, StatutPaiement
from models.session import Session as SessionModel
from models.achat_article import AchatArticle
from models.article import Article
from models.article_categorie import ArticleCategorie
from models.user import User, UserRole
from models.user_group import UserGroup
from models.poste import Poste, PosteEtat


class StatsService:

    # ---------------------------------------------------------
    # 1. REVENUS PAR JOUR
    # ---------------------------------------------------------
    @staticmethod
    def revenus_par_jour(db: Session, jours: int = 30):
        depuis = datetime.utcnow() - timedelta(days=jours)
        rows = (
            db.query(
                func.date(Paiement.date_paiement).label("jour"),
                func.sum(Paiement.montant).label("total")
            )
            .filter(Paiement.statut == StatutPaiement.SUCCES)
            .filter(Paiement.date_paiement >= depuis)
            .group_by(func.date(Paiement.date_paiement))
            .order_by(func.date(Paiement.date_paiement))
            .all()
        )
        return [{"date": r.jour, "total": float(r.total or 0)} for r in rows]

    # ---------------------------------------------------------
    # 2. SESSIONS
    # ---------------------------------------------------------
    @staticmethod
    def sessions_actives_count(db: Session) -> int:
        return db.query(SessionModel).filter(SessionModel.est_active == True).count()

    @staticmethod
    def sessions_aujourdhui_count(db: Session) -> int:
        debut_jour = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return db.query(SessionModel).filter(SessionModel.date_debut >= debut_jour).count()

    # ---------------------------------------------------------
    # 3. ARTICLES LES PLUS VENDUS
    # ---------------------------------------------------------
    @staticmethod
    def articles_plus_vendus(db: Session, limite: int = 5):
        rows = (
            db.query(
                Article.nom,
                func.count(AchatArticle.id).label("quantite"),
                func.sum(AchatArticle.prix).label("total")
            )
            .join(Article, Article.id == AchatArticle.article_id)
            .group_by(Article.id)
            .order_by(func.count(AchatArticle.id).desc())
            .limit(limite)
            .all()
        )
        return [{"nom": r.nom, "quantite": r.quantite, "total": float(r.total or 0)} for r in rows]

    # ---------------------------------------------------------
    # 4. NOUVEAUX CLIENTS PAR JOUR
    # ---------------------------------------------------------
    @staticmethod
    def nouveaux_clients_par_jour(db: Session, jours: int = 30):
        depuis = datetime.utcnow() - timedelta(days=jours)
        rows = (
            db.query(
                func.date(User.date_create).label("jour"),
                func.count(User.id).label("total")
            )
            .filter(User.role == UserRole.client)
            .filter(User.date_create >= depuis)
            .group_by(func.date(User.date_create))
            .order_by(func.date(User.date_create))
            .all()
        )
        return [{"date": r.jour, "total": r.total} for r in rows]

    # ---------------------------------------------------------
    # 5. TAUX D'OCCUPATION DES POSTES
    # ---------------------------------------------------------
    @staticmethod
    def taux_occupation_postes(db: Session) -> dict:
        total = db.query(Poste).count()
        occupes = db.query(Poste).filter(Poste.etat == PosteEtat.OCCUPE).count()
        en_ligne = db.query(Poste).filter(Poste.est_en_ligne == True).count()
        return {
            "total": total,
            "occupes": occupes,
            "en_ligne": en_ligne,
            "taux_occupation": round((occupes / total) * 100, 1) if total else 0.0
        }

    # ---------------------------------------------------------
    # 6. RÉSUMÉ POUR LE TABLEAU DE BORD
    # ---------------------------------------------------------
    @staticmethod
    def resume(db: Session):
        revenus = StatsService.revenus_par_jour(db, jours=30)
        return {
            "revenus_par_jour": revenus,
            "revenu_total_30j": round(sum(r["total"] for r in revenus), 2),
            "sessions_actives": StatsService.sessions_actives_count(db),
            "sessions_aujourdhui": StatsService.sessions_aujourdhui_count(db),
            "articles_plus_vendus": StatsService.articles_plus_vendus(db),
            "nouveaux_clients_par_jour": StatsService.nouveaux_clients_par_jour(db, jours=30),
            "postes": StatsService.taux_occupation_postes(db),
            "total_clients": db.query(User).filter(User.role == UserRole.client).count(),
            "stock": StatsService.resume_stock(db),
        }

    # ---------------------------------------------------------
    # 6bis. INVENTAIRE / STOCK (voir services/article_service.py pour les mouvements)
    # ---------------------------------------------------------
    @staticmethod
    def resume_stock(db: Session) -> dict:
        articles_suivis = db.query(Article).filter(Article.stock.isnot(None)).all()
        valeur_totale = sum((a.stock or 0) * a.prix for a in articles_suivis)
        nb_rupture = sum(1 for a in articles_suivis if (a.stock or 0) <= 0)
        nb_alerte = sum(
            1 for a in articles_suivis
            if a.stock_alerte is not None and 0 < (a.stock or 0) <= a.stock_alerte
        )
        return {
            "nb_articles_suivis": len(articles_suivis),
            "quantite_totale": sum(a.stock or 0 for a in articles_suivis),
            "valeur_totale": round(valeur_totale, 2),
            "nb_rupture": nb_rupture,
            "nb_alerte": nb_alerte,
        }

    # ---------------------------------------------------------
    # 7. STATISTIQUES DÉTAILLÉES (page Statistiques dédiée)
    # ---------------------------------------------------------
    @staticmethod
    def _revenu_periode(db: Session, date_debut: datetime, date_fin: datetime) -> float:
        total = (
            db.query(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut == StatutPaiement.SUCCES)
            .filter(Paiement.date_paiement >= date_debut, Paiement.date_paiement <= date_fin)
            .scalar()
        )
        return float(total or 0)

    @staticmethod
    def revenus_par_jour_periode(db: Session, date_debut: datetime, date_fin: datetime):
        rows = (
            db.query(
                func.date(Paiement.date_paiement).label("jour"),
                func.sum(Paiement.montant).label("total")
            )
            .filter(Paiement.statut == StatutPaiement.SUCCES)
            .filter(Paiement.date_paiement >= date_debut, Paiement.date_paiement <= date_fin)
            .group_by(func.date(Paiement.date_paiement))
            .order_by(func.date(Paiement.date_paiement))
            .all()
        )
        return [{"date": r.jour, "total": float(r.total or 0)} for r in rows]

    @staticmethod
    def ventes_par_categorie(db: Session, date_debut: datetime, date_fin: datetime):
        rows = (
            db.query(
                ArticleCategorie.id, ArticleCategorie.nom, ArticleCategorie.emoji,
                func.count(AchatArticle.id).label("quantite"),
                func.sum(AchatArticle.prix).label("total")
            )
            .select_from(AchatArticle)
            .join(Article, Article.id == AchatArticle.article_id)
            .join(ArticleCategorie, ArticleCategorie.id == Article.categorie_id)
            .filter(AchatArticle.date_achat >= date_debut, AchatArticle.date_achat <= date_fin)
            .group_by(ArticleCategorie.id)
            .order_by(func.sum(AchatArticle.prix).desc())
            .all()
        )
        return [
            {"categorie_id": r.id, "nom": r.nom, "emoji": r.emoji, "quantite": r.quantite, "total": float(r.total or 0)}
            for r in rows
        ]

    @staticmethod
    def usage_par_poste(db: Session, date_debut: datetime, date_fin: datetime):
        rows = (
            db.query(
                Poste.id, Poste.nom,
                func.count(SessionModel.id).label("nb_sessions"),
                func.coalesce(func.sum(SessionModel.consommation_minutes), 0).label("minutes_totales")
            )
            .select_from(SessionModel)
            .join(Poste, Poste.id == SessionModel.poste_id)
            .filter(SessionModel.date_debut >= date_debut, SessionModel.date_debut <= date_fin)
            .group_by(Poste.id)
            .order_by(func.count(SessionModel.id).desc())
            .all()
        )
        return [
            {"poste_id": r.id, "poste_nom": r.nom, "nb_sessions": r.nb_sessions, "minutes_totales": r.minutes_totales}
            for r in rows
        ]

    @staticmethod
    def clients_par_groupe(db: Session, date_debut: datetime, date_fin: datetime):
        groupes = db.query(UserGroup).all()
        resultat = []
        for g in groupes:
            nb_clients = db.query(User).filter(User.groupes.any(UserGroup.id == g.id)).count()
            revenu = (
                db.query(func.coalesce(func.sum(Paiement.montant), 0))
                .join(User, User.id == Paiement.user_id)
                .filter(User.groupes.any(UserGroup.id == g.id))
                .filter(Paiement.statut == StatutPaiement.SUCCES)
                .filter(Paiement.date_paiement >= date_debut, Paiement.date_paiement <= date_fin)
                .scalar()
            )
            resultat.append({
                "groupe_id": g.id, "nom": g.nom, "nb_clients": nb_clients, "revenu": float(revenu or 0)
            })

        sans_groupe = db.query(User).filter(User.role == UserRole.client, ~User.groupes.any()).count()
        if sans_groupe:
            revenu_sans_groupe = (
                db.query(func.coalesce(func.sum(Paiement.montant), 0))
                .join(User, User.id == Paiement.user_id)
                .filter(~User.groupes.any())
                .filter(Paiement.statut == StatutPaiement.SUCCES)
                .filter(Paiement.date_paiement >= date_debut, Paiement.date_paiement <= date_fin)
                .scalar()
            )
            resultat.append({
                "groupe_id": None, "nom": "Sans groupe", "nb_clients": sans_groupe,
                "revenu": float(revenu_sans_groupe or 0)
            })

        return sorted(resultat, key=lambda r: r["revenu"], reverse=True)

    @staticmethod
    def detaille(db: Session, date_debut: datetime, date_fin: datetime):
        duree = date_fin - date_debut
        date_debut_precedente = date_debut - duree
        date_fin_precedente = date_debut

        revenu_actuel = StatsService._revenu_periode(db, date_debut, date_fin)
        revenu_precedent = StatsService._revenu_periode(db, date_debut_precedente, date_fin_precedente)
        variation_pct = (
            round(((revenu_actuel - revenu_precedent) / revenu_precedent) * 100, 1)
            if revenu_precedent else None
        )

        return {
            "periode": {"debut": date_debut.isoformat(), "fin": date_fin.isoformat()},
            "revenus_par_jour": StatsService.revenus_par_jour_periode(db, date_debut, date_fin),
            "revenu_total": round(revenu_actuel, 2),
            "revenu_periode_precedente": round(revenu_precedent, 2),
            "variation_pct": variation_pct,
            "ventes_par_categorie": StatsService.ventes_par_categorie(db, date_debut, date_fin),
            "usage_par_poste": StatsService.usage_par_poste(db, date_debut, date_fin),
            "clients_par_groupe": StatsService.clients_par_groupe(db, date_debut, date_fin),
            "articles_plus_vendus": StatsService.articles_plus_vendus(db, limite=10),
            "nouveaux_clients": db.query(User).filter(
                User.role == UserRole.client, User.date_create >= date_debut, User.date_create <= date_fin
            ).count(),
            "stock": StatsService.resume_stock(db),
        }
