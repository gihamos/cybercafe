from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.article_categorie import ArticleCategorie
from schemas.article_schema import ArticleCategorieCreate, ArticleCategorieUpdate
from services.article_categorie_service import ArticleCategorieService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/article-categorie",
    tags=["categories d'articles"],
    dependencies=[Depends(auth_dependency)]
)


def _serialize(categorie: ArticleCategorie) -> dict:
    return {
        "id": categorie.id,
        "nom": categorie.nom,
        "emoji": categorie.emoji,
        "description": categorie.description,
        "date_creation": categorie.date_creation,
        "nb_articles": len(categorie.articles),
    }


@router.get("/")
def lister(db: Session = Depends(get_db)):
    return {"status_code": 200, "data": [_serialize(c) for c in ArticleCategorieService.lister(db)]}


@router.post("/", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def creer(data: ArticleCategorieCreate, db: Session = Depends(get_db)):
    try:
        categorie = ArticleCategorieService.creer(db=db, nom=data.nom, emoji=data.emoji, description=data.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(categorie)}


@router.patch("/{categorie_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update(categorie_id: int, data: ArticleCategorieUpdate, db: Session = Depends(get_db)):
    try:
        categorie = ArticleCategorieService.update(db=db, categorie_id=categorie_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(categorie)}


@router.delete("/{categorie_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def supprimer(categorie_id: int, db: Session = Depends(get_db)):
    try:
        ArticleCategorieService.supprimer(db=db, categorie_id=categorie_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
