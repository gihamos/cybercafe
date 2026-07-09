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
        categorie_id: int | None = None,
        metadatas: dict | None = None,
        stock: int | None = None,
        stock_alerte: int | None = None
    ):
        if prix <= 0:
            raise ValueError("Le prix doit être supérieur à 0")

        article = Article(
            nom=nom,
            prix=prix,
            description=description,
            categorie_id=categorie_id,
            metadatas=metadatas,
            stock=stock,
            stock_alerte=stock_alerte,
            actif=True
        )

        db.add(article)
        db.commit()
        db.refresh(article)

        HistoriqueService.log(
            db=db,
            type_evenement="article_create",
            description=f"Création de l'article {nom}",
            details={"prix": prix, "categorie_id": categorie_id}
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
        categorie_id: int | None = None,
        actif: bool | None = None,
        prix_min: float | None = None,
        prix_max: float | None = None
    ):
        query = db.query(Article)

        if nom:
            query = query.filter(Article.nom.ilike(f"%{nom}%"))

        if categorie_id:
            query = query.filter(Article.categorie_id == categorie_id)

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

        if article.stock is not None and article.stock <= 0:
            raise ValueError(f"Rupture de stock pour '{article.nom}'")

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

        if article.stock is not None:
            article.stock -= 1

        db.commit()
        db.refresh(achat_article)

        HistoriqueService.log(
            db=db,
            type_evenement="article_buy",
            description=f"Achat de l'article {article.nom}",
            user_id=user_id,
            ticket_id=ticket_id,
            details={"prix": montant, "stock_restant": article.stock}
        )

        if article.stock is not None and article.stock_alerte is not None and article.stock <= article.stock_alerte:
            NotificationService.send_system(
                db=db,
                titre="Stock faible",
                message=f"Il ne reste que {article.stock} unité(s) de '{article.nom}' en stock.",
                details={"article_id": article.id, "stock": article.stock}
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

    # ---------------------------------------------------------
    # 7. HISTORIQUE DES VENTES (pour reçus et statistiques)
    # ---------------------------------------------------------
    @staticmethod
    def lister_ventes(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        user_id: int | None = None,
        date_debut=None,
        date_fin=None,
    ) -> list[AchatArticle]:
        query = db.query(AchatArticle)
        if user_id:
            query = query.filter(AchatArticle.user_id == user_id)
        if date_debut:
            query = query.filter(AchatArticle.date_achat >= date_debut)
        if date_fin:
            query = query.filter(AchatArticle.date_achat <= date_fin)
        return (
            query.order_by(AchatArticle.date_achat.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_vente(db: Session, achat_article_id: int) -> AchatArticle:
        achat = db.query(AchatArticle).get(achat_article_id)
        if not achat:
            raise ValueError("Vente introuvable")
        return achat

    # ---------------------------------------------------------
    # 8. RÉAPPROVISIONNER LE STOCK
    # ---------------------------------------------------------
    @staticmethod
    def reapprovisionner(db: Session, article_id: int, quantite: int) -> Article:
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")
        if quantite <= 0:
            raise ValueError("La quantité doit être positive")

        article.stock = (article.stock or 0) + quantite
        db.commit()
        db.refresh(article)

        HistoriqueService.log(
            db=db,
            type_evenement="article_stock_update",
            description=f"Réapprovisionnement de '{article.nom}' (+{quantite})",
            details={"nouveau_stock": article.stock}
        )
        return article
