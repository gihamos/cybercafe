from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.paiement import Paiement, StatutPaiement
from models.session import Session as SessionModel
from models.achat_article import AchatArticle
from models.article import Article
from models.user import User, UserRole
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
        }
