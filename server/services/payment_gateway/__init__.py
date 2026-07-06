from services.payment_gateway.base import PaymentGateway, PaymentOrder
from services.payment_gateway.paypal_gateway import PayPalGateway

# Pour ajouter une nouvelle passerelle (ex: Stripe) : implémenter PaymentGateway dans
# un nouveau fichier de ce dossier, puis l'enregistrer ici — rien d'autre à changer
# côté services/paiement_service.py ou routers.
_GATEWAYS = {
    "paypal": PayPalGateway,
}


def get_gateway(nom: str) -> PaymentGateway:
    gateway_cls = _GATEWAYS.get(nom)
    if not gateway_cls:
        raise ValueError(f"Passerelle de paiement inconnue : {nom}")
    return gateway_cls()


__all__ = ["PaymentGateway", "PaymentOrder", "get_gateway"]
