from sqlalchemy.orm import Session

from models.article_categorie import ArticleCategorie
from services.historique_service import HistoriqueService


class ArticleCategorieService:

    @staticmethod
    def creer(db: Session, nom: str, emoji: str | None = None, description: str | None = None) -> ArticleCategorie:
        if db.query(ArticleCategorie).filter(ArticleCategorie.nom == nom).first():
            raise ValueError(f"La catégorie '{nom}' existe déjà")

        categorie = ArticleCategorie(nom=nom, emoji=emoji, description=description)
        db.add(categorie)
        db.commit()
        db.refresh(categorie)

        HistoriqueService.log(db=db, type_evenement="article_categorie_create", description=f"Création de la catégorie '{nom}'")
        return categorie

    @staticmethod
    def lister(db: Session) -> list[ArticleCategorie]:
        return db.query(ArticleCategorie).order_by(ArticleCategorie.nom.asc()).all()

    @staticmethod
    def update(db: Session, categorie_id: int, data: dict) -> ArticleCategorie:
        categorie = db.query(ArticleCategorie).get(categorie_id)
        if not categorie:
            raise ValueError("Catégorie introuvable")

        for field, value in data.items():
            if value is not None:
                setattr(categorie, field, value)

        db.commit()
        HistoriqueService.log(db=db, type_evenement="article_categorie_update", description=f"Modification de la catégorie '{categorie.nom}'")
        return categorie

    @staticmethod
    def supprimer(db: Session, categorie_id: int) -> None:
        categorie = db.query(ArticleCategorie).get(categorie_id)
        if not categorie:
            raise ValueError("Catégorie introuvable")

        db.delete(categorie)
        db.commit()
        HistoriqueService.log(db=db, type_evenement="article_categorie_delete", description=f"Suppression de la catégorie '{categorie.nom}'")

    # ---------------------------------------------------------
    # IMAGE DE CATÉGORIE (remplace l'emoji dans les interfaces)
    # ---------------------------------------------------------
    @staticmethod
    def set_image(db: Session, categorie_id: int, contenu: bytes, content_type: str | None) -> ArticleCategorie:
        import io
        import uuid
        from params import STORAGE_PROVIDER
        from services.storage_provider import get_provider

        categorie = db.query(ArticleCategorie).get(categorie_id)
        if not categorie:
            raise ValueError("Catégorie introuvable")

        provider = get_provider(STORAGE_PROVIDER)
        ancienne_cle = categorie.image_cle_stockage
        cle = f"categories/{categorie_id}/{uuid.uuid4().hex}.img"
        provider.upload(cle, io.BytesIO(contenu))

        categorie.image_cle_stockage = cle
        categorie.image_content_type = content_type
        db.commit()
        db.refresh(categorie)

        if ancienne_cle:
            provider.delete(ancienne_cle)
        return categorie

    @staticmethod
    def get_image(db: Session, categorie_id: int):
        from params import STORAGE_PROVIDER
        from services.storage_provider import get_provider

        categorie = db.query(ArticleCategorie).get(categorie_id)
        if not categorie or not categorie.image_cle_stockage:
            raise ValueError("Image introuvable")
        provider = get_provider(STORAGE_PROVIDER)
        return categorie, provider.download(categorie.image_cle_stockage)

    @staticmethod
    def supprimer_image(db: Session, categorie_id: int) -> ArticleCategorie:
        from params import STORAGE_PROVIDER
        from services.storage_provider import get_provider

        categorie = db.query(ArticleCategorie).get(categorie_id)
        if not categorie:
            raise ValueError("Catégorie introuvable")
        if categorie.image_cle_stockage:
            get_provider(STORAGE_PROVIDER).delete(categorie.image_cle_stockage)
            categorie.image_cle_stockage = None
            categorie.image_content_type = None
            db.commit()
            db.refresh(categorie)
        return categorie
