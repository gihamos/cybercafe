from sqlalchemy.orm import Session
from datetime import datetime

from models.promotion import Promotion, is_valide_promotion
from services.historique_service import HistoriqueService
from services.promotion_mechanisms import get_mecanisme, liste_mecanismes, PromotionContext


class PromotionService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE PROMOTION
    # ---------------------------------------------------------
    @staticmethod
    def creer(
        db: Session,
        nom: str,
        mecanisme: str,
        valeur: float,
        code: str | None = None,
        offre_id: int | None = None,
        article_id: int | None = None,
        date_fin: datetime | None = None,
        usage_max: int | None = None,
        parametres: dict | None = None
    ):
        # lève ValueError si le mécanisme n'est pas enregistré (registre extensible,
        # voir services/promotion_mechanisms/)
        get_mecanisme(mecanisme)

        if valeur <= 0:
            raise ValueError("La valeur de la réduction doit être positive")

        if mecanisme == "pourcentage" and valeur > 100:
            raise ValueError("Un pourcentage de réduction ne peut pas dépasser 100")

        code_normalise = code.strip().upper() if code else None
        if code_normalise and db.query(Promotion).filter(Promotion.code == code_normalise).first():
            raise ValueError(f"Le code promo '{code_normalise}' existe déjà")

        promo = Promotion(
            nom=nom,
            code=code_normalise,
            mecanisme=mecanisme,
            valeur=valeur,
            parametres=parametres,
            offre_id=offre_id,
            article_id=article_id,
            date_fin=date_fin,
            usage_max=usage_max,
            actif=True
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)

        HistoriqueService.log(
            db=db,
            type_evenement="promotion_create",
            description=f"Création de la promotion {nom}",
            details={"code": code_normalise, "mecanisme": mecanisme, "valeur": valeur}
        )

        return promo

    # ---------------------------------------------------------
    # 2. METTRE À JOUR
    # ---------------------------------------------------------
    @staticmethod
    def update(db: Session, promo_id: int, data: dict):
        promo = db.query(Promotion).get(promo_id)
        if not promo:
            raise ValueError("Promotion introuvable")

        if data.get("mecanisme"):
            get_mecanisme(data["mecanisme"])

        for key, value in data.items():
            if hasattr(promo, key) and value is not None:
                setattr(promo, key, value)

        db.commit()
        db.refresh(promo)

        HistoriqueService.log(
            db=db,
            type_evenement="promotion_update",
            description=f"Modification de la promotion {promo.nom}",
            details=data
        )

        return promo

    # ---------------------------------------------------------
    # 3. SUPPRIMER
    # ---------------------------------------------------------
    @staticmethod
    def supprimer(db: Session, promo_id: int):
        promo = db.query(Promotion).get(promo_id)
        if not promo:
            raise ValueError("Promotion introuvable")

        nom = promo.nom
        db.delete(promo)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="promotion_delete",
            description=f"Suppression de la promotion {nom}"
        )

        return True

    # ---------------------------------------------------------
    # 4. LISTE / CONSULTATION
    # ---------------------------------------------------------
    @staticmethod
    def lister(db: Session, actif: bool | None = None):
        query = db.query(Promotion)
        if actif is not None:
            query = query.filter(Promotion.actif == actif)
        return query.order_by(Promotion.date_creation.desc()).all()

    @staticmethod
    def get_by_id(db: Session, promo_id: int):
        promo = db.query(Promotion).get(promo_id)
        if not promo:
            raise ValueError("Promotion introuvable")
        return promo

    @staticmethod
    def get_mecanismes_disponibles() -> list[str]:
        return liste_mecanismes()

    # ---------------------------------------------------------
    # 5. RÉSOLUTION D'UNE PROMO AUTOMATIQUE APPLICABLE (sans code)
    # ---------------------------------------------------------
    @staticmethod
    def _get_promo_automatique(db: Session, contexte: PromotionContext):
        query = db.query(Promotion).filter(Promotion.code.is_(None), Promotion.actif == True)
        candidats = []

        if contexte.offre_id is not None:
            candidats += query.filter(Promotion.offre_id == contexte.offre_id).all()
        if contexte.article_id is not None:
            candidats += query.filter(Promotion.article_id == contexte.article_id).all()
        candidats += query.filter(Promotion.offre_id.is_(None), Promotion.article_id.is_(None)).all()

        for promo in candidats:
            if not is_valide_promotion(promo)["valide"]:
                continue
            mecanisme = get_mecanisme(promo.mecanisme)
            applicable, _raison = mecanisme.est_applicable(promo, contexte)
            if applicable:
                return promo

        return None

    # ---------------------------------------------------------
    # 6. APPLIQUER UNE PROMOTION (code fourni, sinon automatique) À UN MONTANT
    # ---------------------------------------------------------
    @staticmethod
    def appliquer(
        db: Session,
        montant: float,
        offre_id: int | None = None,
        article_id: int | None = None,
        code: str | None = None,
        user_id: int | None = None
    ) -> tuple[float, Promotion | None]:
        contexte = PromotionContext(montant=montant, offre_id=offre_id, article_id=article_id, user_id=user_id)

        if code:
            code_normalise = code.strip().upper()
            promo = db.query(Promotion).filter(Promotion.code == code_normalise).first()
            if not promo:
                raise ValueError(f"Code promo '{code}' invalide")

            valide = is_valide_promotion(promo)
            if not valide["valide"]:
                raise ValueError(valide["detail"])

            if promo.offre_id is not None and promo.offre_id != offre_id:
                raise ValueError("Ce code promo ne s'applique pas à cette offre")
            if promo.article_id is not None and promo.article_id != article_id:
                raise ValueError("Ce code promo ne s'applique pas à cet article")

            mecanisme = get_mecanisme(promo.mecanisme)
            applicable, raison = mecanisme.est_applicable(promo, contexte)
            if not applicable:
                raise ValueError(raison or "Ce code promo n'est pas applicable actuellement")
        else:
            promo = PromotionService._get_promo_automatique(db, contexte)

        if not promo:
            return montant, None

        mecanisme = get_mecanisme(promo.mecanisme)
        reduction = mecanisme.calculer_reduction(promo, contexte)
        montant_final = round(max(0.0, montant - reduction), 2)

        promo.usage_count += 1
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="promotion_appliquee",
            description=f"Promotion '{promo.nom}' appliquée : {montant}€ → {montant_final}€",
            user_id=user_id,
            details={"promo_id": promo.id, "montant_original": montant, "montant_final": montant_final}
        )

        return montant_final, promo
