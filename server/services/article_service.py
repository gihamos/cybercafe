import io
import uuid

from sqlalchemy.orm import Session
from models.article import Article
from models.achat_article import AchatArticle, StatutCommande
from models.paiement import TypePaiement, StatutPaiement
from models.mouvement_stock import MouvementStock, TypeMouvementStock
from services.paiement_service import PaiementService
from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from services.promotion_service import PromotionService
from services.storage_provider import get_provider
from models.notification import TypeNotification
from params import STORAGE_PROVIDER


class ArticleService:

    # ---------------------------------------------------------
    # IMAGE DE L'ARTICLE
    # ---------------------------------------------------------
    @staticmethod
    def set_image(db: Session, article_id: int, contenu: bytes, content_type: str | None) -> Article:
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")

        provider = get_provider(STORAGE_PROVIDER)
        ancienne_cle = article.image_cle_stockage
        cle = f"articles/{article_id}/{uuid.uuid4().hex}.img"
        provider.upload(cle, io.BytesIO(contenu))

        article.image_cle_stockage = cle
        article.image_content_type = content_type
        db.commit()
        db.refresh(article)

        if ancienne_cle:
            provider.delete(ancienne_cle)

        return article

    @staticmethod
    def get_image(db: Session, article_id: int):
        article = db.query(Article).get(article_id)
        if not article or not article.image_cle_stockage:
            raise ValueError("Image introuvable")

        provider = get_provider(STORAGE_PROVIDER)
        return article, provider.download(article.image_cle_stockage)

    @staticmethod
    def supprimer_image(db: Session, article_id: int) -> Article:
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")
        if article.image_cle_stockage:
            get_provider(STORAGE_PROVIDER).delete(article.image_cle_stockage)
            article.image_cle_stockage = None
            article.image_content_type = None
            db.commit()
            db.refresh(article)
        return article

    # ---------------------------------------------------------
    # STOCK — journal d'audit (voir models/mouvement_stock.py)
    # ---------------------------------------------------------
    @staticmethod
    def _log_mouvement(
        db: Session, article: Article, type_mouvement: TypeMouvementStock,
        variation: int, motif: str | None = None, operateur_id: int | None = None,
    ) -> None:
        db.add(MouvementStock(
            article_id=article.id,
            type_mouvement=type_mouvement,
            variation=variation,
            stock_apres=article.stock or 0,
            motif=motif,
            operateur_id=operateur_id,
        ))
        db.commit()

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
        stock_alerte: int | None = None,
        code_barre: str | None = None,
        date_peremption=None,
        origine: str | None = None,
        ingredients: str | None = None,
        poids_grammes: float | None = None,
        allergenes: str | None = None,
        type_conservation: str | None = None,
        sku: str | None = None
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
            code_barre=code_barre,
            date_peremption=date_peremption,
            origine=origine,
            ingredients=ingredients,
            type_conservation=type_conservation or "non_perissable",
            sku=sku,
            poids_grammes=poids_grammes,
            allergenes=allergenes,
            actif=True
        )

        db.add(article)
        db.commit()
        db.refresh(article)

        # code unique d'identification (SKU) auto-généré si non fourni
        if not article.sku:
            article.sku = f"ART-{article.id:05d}"
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
        prix_max: float | None = None,
        code_barre: str | None = None
    ):
        query = db.query(Article)

        if code_barre:
            query = query.filter(Article.code_barre == code_barre.strip())

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
        code_promo: str | None = None,
        statut_commande: str | None = None
    ):
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")

        if not article.actif:
            raise ValueError("Cet article n'est pas disponible")

        if article.stock is not None and article.stock <= 0:
            raise ValueError(f"Rupture de stock pour '{article.nom}'")

        montant, promos_appliquees = PromotionService.appliquer(db, article.prix, article_id=article_id, code=code_promo, user_id=user_id)
        # Espèces : « en attente » seulement quand la commande vient d'un poste/portail
        # sans opérateur (le client paiera au comptoir). Un opérateur qui encaisse en
        # caisse reçoit l'argent immédiatement : paiement réglé sur-le-champ.
        en_attente = type_paiement == TypePaiement.ESPECES and operateur_id is None
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
                operateur_id=operateur_id,
                statut=StatutPaiement.EN_ATTENTE if en_attente else StatutPaiement.SUCCES
            )
            paiement_id = paiement.id
            PromotionService.lier_paiement(db, paiement.id, promos_appliquees)

        achat_article = AchatArticle(
            article_id=article_id,
            user_id=user_id,
            ticket_id=ticket_id,
            paiement_id=paiement_id,
            operateur_id=operateur_id,
            prix=montant,
            # vente au comptoir : remise immédiate ; commande portail : à préparer
            statut_commande=statut_commande or StatutCommande.RECUPEREE.value
        )
        db.add(achat_article)

        stock_suivi = article.stock is not None
        if stock_suivi:
            article.stock -= 1

        db.commit()
        db.refresh(achat_article)

        if stock_suivi:
            ArticleService._log_mouvement(
                db, article, TypeMouvementStock.VENTE, -1, operateur_id=operateur_id
            )

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
            "paiement_id": achat_article.paiement_id,
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
    def reapprovisionner(
        db: Session, article_id: int, quantite: int,
        motif: str | None = None, operateur_id: int | None = None,
    ) -> Article:
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")
        if quantite <= 0:
            raise ValueError("La quantité doit être positive")

        article.stock = (article.stock or 0) + quantite
        db.commit()
        db.refresh(article)

        ArticleService._log_mouvement(
            db, article, TypeMouvementStock.ENTREE, quantite, motif=motif, operateur_id=operateur_id
        )

        HistoriqueService.log(
            db=db,
            type_evenement="article_stock_update",
            description=f"Réapprovisionnement de '{article.nom}' (+{quantite})",
            operateur_id=operateur_id,
            details={"nouveau_stock": article.stock}
        )
        return article

    # ---------------------------------------------------------
    # AJUSTEMENT MANUEL DE STOCK (correction d'inventaire)
    # ---------------------------------------------------------
    @staticmethod
    def ajuster_stock(
        db: Session, article_id: int, variation: int,
        motif: str, operateur_id: int | None = None,
    ) -> Article:
        article = db.query(Article).get(article_id)
        if not article:
            raise ValueError("Article introuvable")
        if variation == 0:
            raise ValueError("La variation ne peut pas être nulle")
        if not motif or not motif.strip():
            raise ValueError("Un motif est requis pour un ajustement manuel")

        nouveau_stock = (article.stock or 0) + variation
        if nouveau_stock < 0:
            raise ValueError("Le stock ne peut pas devenir négatif")

        article.stock = nouveau_stock
        db.commit()
        db.refresh(article)

        ArticleService._log_mouvement(
            db, article, TypeMouvementStock.AJUSTEMENT, variation, motif=motif, operateur_id=operateur_id
        )

        HistoriqueService.log(
            db=db,
            type_evenement="article_stock_update",
            description=f"Ajustement de stock de '{article.nom}' ({'+' if variation > 0 else ''}{variation}) — {motif}",
            operateur_id=operateur_id,
            details={"nouveau_stock": article.stock, "motif": motif}
        )
        return article

    # ---------------------------------------------------------
    # HISTORIQUE DES MOUVEMENTS D'UN ARTICLE
    # ---------------------------------------------------------
    @staticmethod
    def lister_mouvements(db: Session, article_id: int, limit: int = 100) -> list[MouvementStock]:
        return (
            db.query(MouvementStock)
            .filter(MouvementStock.article_id == article_id)
            .order_by(MouvementStock.date_mouvement.desc())
            .limit(limit)
            .all()
        )
