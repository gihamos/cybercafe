from sqlalchemy.orm import Session
from datetime import datetime

from models.promotion import Promotion, is_valide_promotion
from models.paiement_promotion import PaiementPromotion
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
    # 5. RÉSOLUTION DES PROMOS AUTOMATIQUES APPLICABLES (sans code, cumulables)
    # ---------------------------------------------------------
    @staticmethod
    def _get_promos_automatiques(db: Session, contexte: PromotionContext) -> list[Promotion]:
        query = db.query(Promotion).filter(Promotion.code.is_(None), Promotion.actif == True)
        candidats = []

        if contexte.offre_id is not None:
            candidats += query.filter(Promotion.offre_id == contexte.offre_id).all()
        if contexte.article_id is not None:
            candidats += query.filter(Promotion.article_id == contexte.article_id).all()
        candidats += query.filter(Promotion.offre_id.is_(None), Promotion.article_id.is_(None)).all()

        vus = set()
        applicables = []
        for promo in candidats:
            if promo.id in vus:
                continue
            vus.add(promo.id)
            if not is_valide_promotion(promo)["valide"]:
                continue
            mecanisme = get_mecanisme(promo.mecanisme)
            applicable, _raison = mecanisme.est_applicable(promo, contexte)
            if applicable:
                applicables.append(promo)

        return applicables

    # ---------------------------------------------------------
    # 6. APPLIQUER LES PROMOTIONS APPLICABLES (automatiques cumulées + code
    #    optionnel en plus) À UN MONTANT — un client peut cumuler plusieurs
    #    promotions automatiques, chacune réduisant le montant restant après
    #    application des précédentes.
    # ---------------------------------------------------------
    @staticmethod
    def appliquer(
        db: Session,
        montant: float,
        offre_id: int | None = None,
        article_id: int | None = None,
        code: str | None = None,
        user_id: int | None = None
    ) -> tuple[float, list[tuple[Promotion, float]]]:
        """Retourne (montant_final, [(promotion, montant_reduit_par_cette_promo), ...]) —
        le détail par promotion permet de les tracer individuellement sur le paiement
        (voir lier_paiement) plutôt que de ne connaître que la remise totale."""
        montant_courant = montant
        promos_appliquees: list[tuple[Promotion, float]] = []

        contexte = PromotionContext(montant=montant_courant, offre_id=offre_id, article_id=article_id, user_id=user_id)
        for promo in PromotionService._get_promos_automatiques(db, contexte):
            ctx = PromotionContext(montant=montant_courant, offre_id=offre_id, article_id=article_id, user_id=user_id)
            mecanisme = get_mecanisme(promo.mecanisme)
            reduction = mecanisme.calculer_reduction(promo, ctx)
            montant_courant = round(max(0.0, montant_courant - reduction), 2)
            promo.usage_count += 1
            promos_appliquees.append((promo, reduction))

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

            ctx = PromotionContext(montant=montant_courant, offre_id=offre_id, article_id=article_id, user_id=user_id)
            mecanisme = get_mecanisme(promo.mecanisme)
            applicable, raison = mecanisme.est_applicable(promo, ctx)
            if not applicable:
                raise ValueError(raison or "Ce code promo n'est pas applicable actuellement")

            reduction = mecanisme.calculer_reduction(promo, ctx)
            montant_courant = round(max(0.0, montant_courant - reduction), 2)
            promo.usage_count += 1
            promos_appliquees.append((promo, reduction))

        if not promos_appliquees:
            return montant, []

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="promotion_appliquee",
            description=f"{len(promos_appliquees)} promotion(s) appliquée(s) : {montant}€ → {montant_courant}€",
            user_id=user_id,
            details={
                "promo_ids": [p.id for p, _ in promos_appliquees],
                "montant_original": montant,
                "montant_final": montant_courant,
            }
        )

        return montant_courant, promos_appliquees

    # ---------------------------------------------------------
    # 7. LIER LES PROMOTIONS APPLIQUÉES À UN PAIEMENT (traçabilité)
    # ---------------------------------------------------------
    @staticmethod
    def lier_paiement(db: Session, paiement_id: int, promos_appliquees: list[tuple[Promotion, float]]) -> None:
        if not promos_appliquees:
            return
        for promo, reduction in promos_appliquees:
            db.add(PaiementPromotion(paiement_id=paiement_id, promotion_id=promo.id, montant_reduction=reduction))
        db.commit()

    # ---------------------------------------------------------
    # 8. VÉRIFIER UN CODE PROMO SANS L'APPLIQUER (aperçu avant encaissement — ne
    #    touche pas usage_count, ne modifie rien, purement en lecture)
    # ---------------------------------------------------------
    @staticmethod
    def verifier_code(
        db: Session, code: str, montant: float,
        offre_id: int | None = None, article_id: int | None = None, user_id: int | None = None,
    ) -> dict:
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

        ctx = PromotionContext(montant=montant, offre_id=offre_id, article_id=article_id, user_id=user_id)
        mecanisme = get_mecanisme(promo.mecanisme)
        applicable, raison = mecanisme.est_applicable(promo, ctx)
        if not applicable:
            raise ValueError(raison or "Ce code promo n'est pas applicable actuellement")

        reduction = round(mecanisme.calculer_reduction(promo, ctx), 2)
        return {
            "id": promo.id,
            "nom": promo.nom,
            "code": promo.code,
            "reduction": reduction,
            "montant_final": round(max(0.0, montant - reduction), 2),
        }
