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
