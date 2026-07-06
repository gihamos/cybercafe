from sqlalchemy.orm import Session
from models.article import Article
from models.achat_article import AchatArticle
from models.paiement import TypePaiement, StatutPaiement
from services.paiement_service import PaiementService
from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from services.promotion_service import PromotionService
from models.notification import TypeNotification


class ArticleService:

    # ---------------------------------------------------------
    # 1. CRÉER UN ARTICLE
    # ---------------------------------------------------------
    @staticmethod
    def creer_article(
        db: Session,
        nom: str,
        prix: float,
        description: str | None = None,
        categorie: str | None = None,
        metadatas: dict | None = None
    ):
        if prix <= 0:
            raise ValueError("Le prix doit être supérieur à 0")

        article = Article(
            nom=nom,
            prix=prix,
            description=description,
            categorie=categorie,
            metadatas=metadatas,
            actif=True
        )

        db.add(article)
        db.commit()
        db.refresh(article)

        HistoriqueService.log(
            db=db,
            type_evenement="article_create",
            description=f"Création de l'article {nom}",
            details={"prix": prix, "categorie": categorie}
        )

        return article

    # ---------------------------------------------------------
    # 2. METTRE À JOUR UN ARTICLE
    # ---------------------------------------------------------
    @staticmethod
    def update_article(db: Session, article_id: int, data: dict):
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")

        for key, value in data.items():
            if hasattr(article, key) and value is not None:
                setattr(article, key, value)

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="article_update",
            description=f"Modification de l'article {article.nom}",
            details=data
        )

        return article

    # ---------------------------------------------------------
    # 3. ACTIVER / DÉSACTIVER UN ARTICLE
    # ---------------------------------------------------------
    @staticmethod
    def set_actif(db: Session, article_id: int, actif: bool):
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")

        article.actif = actif
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="article_status",
            description=f"Article {article.nom} {'activé' if actif else 'désactivé'}"
        )

        return article

    # ---------------------------------------------------------
    # 4. SUPPRIMER UN ARTICLE
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_article(db: Session, article_id: int):
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")

        db.delete(article)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="article_delete",
            description=f"Suppression de l'article {article.nom}"
        )

        return True

    # ---------------------------------------------------------
    # 5. LISTE + FILTRES
    # ---------------------------------------------------------
    @staticmethod
    def rechercher_articles(
        db: Session,
        nom: str | None = None,
        categorie: str | None = None,
        actif: bool | None = None,
        prix_min: float | None = None,
        prix_max: float | None = None
    ):
        query = db.query(Article)

        if nom:
            query = query.filter(Article.nom.ilike(f"%{nom}%"))

        if categorie:
            query = query.filter(Article.categorie == categorie)

        if actif is not None:
            query = query.filter(Article.actif == actif)

        if prix_min is not None:
            query = query.filter(Article.prix >= prix_min)

        if prix_max is not None:
            query = query.filter(Article.prix <= prix_max)

        return query.order_by(Article.nom.asc()).all()

    # ---------------------------------------------------------
    # 6. ACHETER UN ARTICLE (paiement direct ou via solde)
    # ---------------------------------------------------------
    @staticmethod
    def acheter_article(
        db: Session,
        article_id: int,
        user_id: int | None = None,
        ticket_id: int | None = None,
        operateur_id: int | None = None,
        type_paiement: TypePaiement | None = None,
        utiliser_solde: bool = False,
        code_promo: str | None = None
    ):
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")

        if not article.actif:
            raise ValueError("Cet article n'est pas disponible")

        montant, _promo = PromotionService.appliquer(db, article.prix, article_id=article_id, code=code_promo, user_id=user_id)
        en_attente = type_paiement == TypePaiement.ESPECES
        paiement_id = None

        # Paiement via solde utilisateur
        if utiliser_solde:
            if not user_id:
                raise ValueError("Le paiement via solde nécessite un utilisateur")
            PaiementService.payer_via_solde(db, user_id, montant)

        # Paiement direct (espèces, carte…)
        else:
            paiement = PaiementService.creer_paiement(
                db=db,
                montant=montant,
                type_paiement=type_paiement,
                user_id=user_id,
                ticket_id=ticket_id,
                statut=StatutPaiement.EN_ATTENTE if en_attente else StatutPaiement.SUCCES
            )
            paiement_id = paiement.id

        achat_article = AchatArticle(
            article_id=article_id,
            user_id=user_id,
            ticket_id=ticket_id,
            paiement_id=paiement_id,
            operateur_id=operateur_id,
            prix=montant
        )
        db.add(achat_article)
        db.commit()
        db.refresh(achat_article)

        HistoriqueService.log(
            db=db,
            type_evenement="article_buy",
            description=f"Achat de l'article {article.nom}",
            user_id=user_id,
            ticket_id=ticket_id,
            details={"prix": montant}
        )

        # Notification utilisateur
        if user_id:
            message = (
                f"Votre achat de l'article {article.nom} ({montant}€) est en attente de paiement à la caisse."
                if en_attente else
                f"Vous avez acheté l'article {article.nom} ({montant}€)."
            )
            NotificationService.send_to_user(
                db=db,
                user_id=user_id,
                titre="Achat effectué",
                message=message,
                type_notification=TypeNotification.PAIEMENT
            )

        return {
            "status": "en_attente" if en_attente else "ok",
            "achat_article_id": achat_article.id,
            "article": article.nom,
            "prix": montant
        }
