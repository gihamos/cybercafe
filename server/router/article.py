from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.article import Article
from models.paiement import TypePaiement
from schemas.article_schema import ArticleCreate, ArticleUpdate
from services.article_service import ArticleService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user


router = APIRouter(prefix="/article", tags=["articles"], dependencies=[Depends(auth_dependency)])


def _serialize(article: Article) -> dict:
    return {
        "id": article.id,
        "nom": article.nom,
        "description": article.description,
        "prix": article.prix,
        "categorie": article.categorie,
        "actif": article.actif,
        "metadatas": article.metadatas,
    }


@router.post("/", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def creer_article(data: ArticleCreate, db: Session = Depends(get_db)):
    try:
        article = ArticleService.creer_article(db=db, **data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(article)}


@router.get("/")
def rechercher_articles(
    nom: str | None = None,
    categorie: str | None = None,
    actif: bool | None = None,
    prix_min: float | None = None,
    prix_max: float | None = None,
    db: Session = Depends(get_db)
):
    articles = ArticleService.rechercher_articles(
        db=db, nom=nom, categorie=categorie, actif=actif, prix_min=prix_min, prix_max=prix_max
    )
    return {"status_code": 200, "data": [_serialize(a) for a in articles]}


@router.patch("/{article_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update_article(article_id: int, data: ArticleUpdate, db: Session = Depends(get_db)):
    try:
        article = ArticleService.update_article(db=db, article_id=article_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.patch("/{article_id}/actif", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def set_actif(article_id: int, actif: bool, db: Session = Depends(get_db)):
    try:
        article = ArticleService.set_actif(db=db, article_id=article_id, actif=actif)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.delete("/{article_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def supprimer_article(article_id: int, db: Session = Depends(get_db)):
    try:
        ArticleService.supprimer_article(db=db, article_id=article_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}


@router.post("/{article_id}/acheter", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def acheter_article(
    article_id: int,
    user_id: int | None = None,
    ticket_id: int | None = None,
    type_paiement: TypePaiement | None = None,
    utiliser_solde: bool = False,
    code_promo: str | None = None,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = ArticleService.acheter_article(
            db=db,
            article_id=article_id,
            user_id=user_id,
            ticket_id=ticket_id,
            operateur_id=currentuser.get("id"),
            type_paiement=type_paiement,
            utiliser_solde=utiliser_solde,
            code_promo=code_promo
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": result}
