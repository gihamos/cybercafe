from services.promotion_mechanisms.base import PromotionMechanism, PromotionContext


class MontantFixeMechanism(PromotionMechanism):
    """Mécanisme intégré : réduction d'un montant fixe (Promotion.valeur, en €)."""

    def est_applicable(self, promo, contexte: PromotionContext) -> tuple[bool, str]:
        return True, ""

    def calculer_reduction(self, promo, contexte: PromotionContext) -> float:
        return promo.valeur
