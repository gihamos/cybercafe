from services.in_person_gateway.base import InPersonGateway, PaymentResult
from services.in_person_gateway.carte_gateway import CarteGateway
from services.in_person_gateway.mobile_money_gateway import MobileMoneyGateway

# Pour ajouter un nouveau fournisseur (ex: un autre processeur carte) : implémenter
# InPersonGateway dans un nouveau fichier de ce dossier, puis l'enregistrer ici — rien
# d'autre à changer côté services/paiement_service.py ou routers. Le virement bancaire
# n'a volontairement pas de gateway : contrairement à la carte/mobile money, un virement
# SEPA classique n'a pas d'API de validation synchrone — il est confirmé manuellement par
# l'opérateur au vu du relevé bancaire (voir PaiementService.encaisser_caisse).
_GATEWAYS = {
    "carte": CarteGateway,
    "mobile_money": MobileMoneyGateway,
}


def get_in_person_gateway(type_paiement: str) -> InPersonGateway | None:
    gateway_cls = _GATEWAYS.get(type_paiement)
    return gateway_cls() if gateway_cls else None


def liste_in_person_gateways() -> list[str]:
    return list(_GATEWAYS.keys())


__all__ = ["InPersonGateway", "PaymentResult", "get_in_person_gateway", "liste_in_person_gateways"]
