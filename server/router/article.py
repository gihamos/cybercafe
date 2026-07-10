from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.article import Article
from models.paiement import TypePaiement
from schemas.article_schema import ArticleCreate, ArticleUpdate
from services.article_service import ArticleService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission, get_current_user


router = APIRouter(prefix="/article", tags=["articles"], dependencies=[Depends(auth_dependency)])


def _serialize(article: Article) -> dict:
    return {
        "id": article.id,
        "nom": article.nom,
        "description": article.description,
        "prix": article.prix,
        "categorie_id": article.categorie_id,
        "categorie_nom": article.categorie.nom if article.categorie else None,
        "categorie_emoji": article.categorie.emoji if article.categorie else None,
        "actif": article.actif,
        "metadatas": article.metadatas,
        "stock": article.stock,
        "stock_alerte": article.stock_alerte,
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
    categorie_id: int | None = None,
    actif: bool | None = None,
    prix_min: float | None = None,
    prix_max: float | None = None,
    db: Session = Depends(get_db)
):
    articles = ArticleService.rechercher_articles(
        db=db, nom=nom, categorie_id=categorie_id, actif=actif, prix_min=prix_min, prix_max=prix_max
    )
    return {"status_code": 200, "data": [_serialize(a) for a in articles]}


@router.patch("/{article_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update_article(article_id: int, data: ArticleUpdate, db: Session = Depends(get_db)):
    try:
        article = ArticleService.update_article(db=db, article_id=article_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.post("/{article_id}/reapprovisionner", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("catalogue"))])
def reapprovisionner(article_id: int, quantite: int, db: Session = Depends(get_db)):
    try:
        article = ArticleService.reapprovisionner(db=db, article_id=article_id, quantite=quantite)
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


def _serialize_vente(achat) -> dict:
    return {
        "id": achat.id,
        "article_id": achat.article_id,
        "article_nom": achat.article.nom if achat.article else None,
        "prix": achat.prix,
        "user_id": achat.user_id,
        "user_nom": achat.user.username if achat.user else None,
        "ticket_id": achat.ticket_id,
        "operateur_id": achat.operateur_id,
        "operateur_nom": achat.operateur.username if achat.operateur else None,
        "paiement_id": achat.paiement_id,
        "date_achat": achat.date_achat,
    }


@router.get("/ventes/liste")
def lister_ventes(
    limit: int = 50, offset: int = 0, user_id: int | None = None,
    db: Session = Depends(get_db)
):
    ventes = ArticleService.lister_ventes(db=db, limit=limit, offset=offset, user_id=user_id)
    return {"status_code": 200, "data": [_serialize_vente(v) for v in ventes]}


@router.get("/ventes/{achat_article_id}")
def get_vente(achat_article_id: int, db: Session = Depends(get_db)):
    try:
        achat = ArticleService.get_vente(db=db, achat_article_id=achat_article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize_vente(achat)}


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
