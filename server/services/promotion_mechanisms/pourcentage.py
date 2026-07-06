from services.promotion_mechanisms.base import PromotionMechanism, PromotionContext


class PourcentageMechanism(PromotionMechanism):
    """Mécanisme intégré : réduction de Promotion.valeur pour cent du montant."""

    def est_applicable(self, promo, contexte: PromotionContext) -> tuple[bool, str]:
        return True, ""

    def calculer_reduction(self, promo, contexte: PromotionContext) -> float:
        return contexte.montant * (promo.valeur / 100)
