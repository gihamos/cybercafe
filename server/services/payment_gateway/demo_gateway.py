import uuid

from services.payment_gateway.base import PaymentGateway, PaymentOrder


class DemoGateway(PaymentGateway):
    """Passerelle de démonstration/développement : aucune API externe. La commande est
    approuvée par le payeur via l'endpoint public `confirmer-demo` du portail (protégé
    par le secret par commande stocké dans Paiement.details), qui joue le rôle du
    retour de redirection d'une vraie passerelle. À NE PAS activer en production —
    remplacer par paypal (ou une autre passerelle réelle) dans les appels."""

    nom = "demo"

    def creer_commande(self, montant: float, devise: str, reference: str, description: str) -> PaymentOrder:
        order_id = f"demo-{uuid.uuid4().hex}"
        return PaymentOrder(
            order_id=order_id,
            # Schéma spécial reconnu par le portail : il affiche un bouton "Payer
            # (démo)" au lieu de rediriger vers un site de paiement externe.
            approval_url=f"demo://approve/{order_id}",
            statut="CREATED",
            montant=montant,
            devise=devise,
            raw={"reference": reference, "description": description},
        )

    def capturer_commande(self, order_id: str) -> PaymentOrder:
        return PaymentOrder(
            order_id=order_id, approval_url=None, statut="COMPLETED",
            montant=0, devise="EUR", raw={},
        )

    def verifier_webhook(self, headers: dict, raw_body: bytes) -> dict | None:
        # Pas de webhook pour la passerelle démo : la confirmation passe uniquement
        # par l'endpoint confirmer-demo (secret par commande).
        return None
