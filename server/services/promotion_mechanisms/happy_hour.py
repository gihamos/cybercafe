from services.promotion_mechanisms.base import PromotionMechanism, PromotionContext


class HappyHourMechanism(PromotionMechanism):
    """Exemple de mécanisme personnalisé : réduction de Promotion.valeur % (ou €
    selon Promotion.parametres["type"]), applicable uniquement pendant une plage
    horaire donnée.

    Promotion.parametres attendus :
        {"heure_debut": 18, "heure_fin": 20, "type": "pourcentage"}
    "type" vaut "pourcentage" (défaut) ou "montant_fixe".

    Sert de modèle pour écrire un mécanisme personnalisé : la condition
    d'applicabilité (ici l'heure) est vérifiée dans est_applicable, le calcul du
    montant de réduction dans calculer_reduction. Enregistré dans __init__.py."""

    def est_applicable(self, promo, contexte: PromotionContext) -> tuple[bool, str]:
        params = promo.parametres or {}
        heure_debut = params.get("heure_debut", 0)
        heure_fin = params.get("heure_fin", 23)
        heure_actuelle = contexte.moment.hour

        if heure_debut <= heure_actuelle < heure_fin:
            return True, ""

        return False, f"Cette promotion n'est valable qu'entre {heure_debut}h et {heure_fin}h"

    def calculer_reduction(self, promo, contexte: PromotionContext) -> float:
        params = promo.parametres or {}
        if params.get("type", "pourcentage") == "montant_fixe":
            return promo.valeur
        return contexte.montant * (promo.valeur / 100)
