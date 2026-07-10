from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.promotion import Promotion
from schemas.promotion_schema import PromotionCreate, PromotionUpdate
from services.promotion_service import PromotionService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission


router = APIRouter(
    prefix="/promotion",
    tags=["promotions"],
    dependencies=[
        Depends(auth_dependency),
        Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])),
        Depends(require_permission("catalogue")),
    ]
)


def _serialize(promo: Promotion) -> dict:
    return {
        "id": promo.id,
        "nom": promo.nom,
        "code": promo.code,
        "mecanisme": promo.mecanisme,
        "valeur": promo.valeur,
        "parametres": promo.parametres,
        "offre_id": promo.offre_id,
        "article_id": promo.article_id,
        "date_debut": promo.date_debut,
        "date_fin": promo.date_fin,
        "usage_max": promo.usage_max,
        "usage_count": promo.usage_count,
        "actif": promo.actif,
        "date_creation": promo.date_creation,
    }


@router.get("/mecanismes")
def lister_mecanismes():
    """Clés de mécanismes de promotion disponibles (intégrés + personnalisés
    enregistrés dans services/promotion_mechanisms/)."""
    return {"status_code": 200, "data": PromotionService.get_mecanismes_disponibles()}


@router.post("/", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def creer_promotion(data: PromotionCreate, db: Session = Depends(get_db)):
    try:
        promo = PromotionService.creer(db=db, **data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": _serialize(promo)}


@router.get("/")
def lister_promotions(actif: bool | None = None, db: Session = Depends(get_db)):
    promos = PromotionService.lister(db=db, actif=actif)
    return {"status_code": 200, "data": [_serialize(p) for p in promos]}


@router.get("/{promo_id}")
def get_promotion(promo_id: int, db: Session = Depends(get_db)):
    try:
        promo = PromotionService.get_by_id(db, promo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(promo)}


@router.patch("/{promo_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update_promotion(promo_id: int, data: PromotionUpdate, db: Session = Depends(get_db)):
    try:
        promo = PromotionService.update(db=db, promo_id=promo_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(promo)}


@router.delete("/{promo_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def supprimer_promotion(promo_id: int, db: Session = Depends(get_db)):
    try:
        PromotionService.supprimer(db=db, promo_id=promo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}
