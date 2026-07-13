from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
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
        "a_une_image": article.image_cle_stockage is not None,
        "code_barre": article.code_barre,
        "date_peremption": article.date_peremption,
        "origine": article.origine,
        "ingredients": article.ingredients,
        "poids_grammes": article.poids_grammes,
        "allergenes": article.allergenes,
        "sku": article.sku,
        "type_conservation": article.type_conservation,
        "categorie_a_une_image": article.categorie.image_cle_stockage is not None if article.categorie else False,
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
    code_barre: str | None = None,
    db: Session = Depends(get_db)
):
    articles = ArticleService.rechercher_articles(
        db=db, nom=nom, categorie_id=categorie_id, actif=actif, prix_min=prix_min, prix_max=prix_max, code_barre=code_barre
    )
    return {"status_code": 200, "data": [_serialize(a) for a in articles]}


@router.patch("/{article_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update_article(article_id: int, data: ArticleUpdate, db: Session = Depends(get_db)):
    try:
        article = ArticleService.update_article(db=db, article_id=article_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.post("/{article_id}/image", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
async def uploader_image(article_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    contenu = await file.read()
    try:
        article = ArticleService.set_image(db=db, article_id=article_id, contenu=contenu, content_type=file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.get("/{article_id}/image")
def telecharger_image(article_id: int, db: Session = Depends(get_db)):
    try:
        article, flux = ArticleService.get_image(db=db, article_id=article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(flux, media_type=article.image_content_type or "application/octet-stream")


@router.delete("/{article_id}/image", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def supprimer_image(article_id: int, db: Session = Depends(get_db)):
    try:
        article = ArticleService.supprimer_image(db=db, article_id=article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.post("/{article_id}/reapprovisionner", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("gestion_stock"))])
def reapprovisionner(
    article_id: int, quantite: int, motif: str | None = None,
    currentuser=Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        article = ArticleService.reapprovisionner(
            db=db, article_id=article_id, quantite=quantite, motif=motif, operateur_id=currentuser.get("id")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


@router.post(
    "/{article_id}/ajuster-stock",
    dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("gestion_stock"))]
)
def ajuster_stock(
    article_id: int, variation: int, motif: str,
    currentuser=Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        article = ArticleService.ajuster_stock(
            db=db, article_id=article_id, variation=variation, motif=motif, operateur_id=currentuser.get("id")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(article)}


def _serialize_mouvement(m) -> dict:
    return {
        "id": m.id,
        "article_id": m.article_id,
        "type_mouvement": m.type_mouvement,
        "variation": m.variation,
        "stock_apres": m.stock_apres,
        "motif": m.motif,
        "operateur_id": m.operateur_id,
        "operateur_nom": m.operateur.username if m.operateur else None,
        "date_mouvement": m.date_mouvement,
    }


@router.get(
    "/{article_id}/mouvements",
    dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("gestion_stock"))]
)
def lister_mouvements(article_id: int, limit: int = 100, db: Session = Depends(get_db)):
    mouvements = ArticleService.lister_mouvements(db=db, article_id=article_id, limit=limit)
    return {"status_code": 200, "data": [_serialize_mouvement(m) for m in mouvements]}


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
        "user_nom_complet": (
            (" ".join(p for p in [achat.user.first_name, achat.user.last_name] if p) or achat.user.username)
            if achat.user else None
        ),
        "ticket_id": achat.ticket_id,
        "operateur_id": achat.operateur_id,
        "operateur_nom": achat.operateur.username if achat.operateur else None,
        "paiement_id": achat.paiement_id,
        "statut_commande": achat.statut_commande,
        "date_achat": achat.date_achat,
    }


@router.get("/ventes/liste")
def lister_ventes(
    limit: int = 50, offset: int = 0, user_id: int | None = None,
    db: Session = Depends(get_db)
):
    ventes = ArticleService.lister_ventes(db=db, limit=limit, offset=offset, user_id=user_id)
    return {"status_code": 200, "data": [_serialize_vente(v) for v in ventes]}


@router.patch("/ventes/{achat_article_id}/statut", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def changer_statut_vente(achat_article_id: int, statut: str, db: Session = Depends(get_db)):
    """Suivi de commande : à préparer → prête → récupérée (commandes du portail)."""
    from models.achat_article import AchatArticle, StatutCommande
    if statut not in [s.value for s in StatutCommande]:
        raise HTTPException(status_code=400, detail="Statut invalide")
    achat = db.query(AchatArticle).get(achat_article_id)
    if not achat:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    achat.statut_commande = statut
    db.commit()
    return {"status_code": 200, "data": _serialize_vente(achat)}


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
