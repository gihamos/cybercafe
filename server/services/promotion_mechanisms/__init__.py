from services.promotion_mechanisms.base import PromotionMechanism, PromotionContext
from services.promotion_mechanisms.pourcentage import PourcentageMechanism
from services.promotion_mechanisms.montant_fixe import MontantFixeMechanism
from services.promotion_mechanisms.happy_hour import HappyHourMechanism

# Pour ajouter un mécanisme personnalisé : implémenter PromotionMechanism dans un
# nouveau fichier de ce dossier, puis l'enregistrer ici — rien d'autre à changer
# côté services/promotion_service.py ou router/promotion.py. Les clés ci-dessous
# sont exposées telles quelles au frontend via GET /promotion/mecanismes.
_MECANISMES = {
    "pourcentage": PourcentageMechanism(),
    "montant_fixe": MontantFixeMechanism(),
    "happy_hour": HappyHourMechanism(),
}


def get_mecanisme(nom: str) -> PromotionMechanism:
    mecanisme = _MECANISMES.get(nom)
    if not mecanisme:
        raise ValueError(f"Mécanisme de promotion inconnu : {nom}")
    return mecanisme


def liste_mecanismes() -> list[str]:
    return list(_MECANISMES.keys())


__all__ = ["PromotionMechanism", "PromotionContext", "get_mecanisme", "liste_mecanismes"]
