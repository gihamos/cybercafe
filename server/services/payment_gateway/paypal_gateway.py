import json

import httpx

from params import (
    PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_API_BASE,
    PAYPAL_WEBHOOK_ID, PAYMENT_RETURN_URL, PAYMENT_CANCEL_URL
)
from services.payment_gateway.base import PaymentGateway, PaymentOrder


class PayPalGateway(PaymentGateway):
    """Intégration PayPal via l'API REST Orders v2 (sandbox par défaut, voir
    params.PAYPAL_MODE). ⚠️ Non testée contre de vrais identifiants sandbox dans cet
    environnement de développement (pas d'accès à un compte PayPal réel) — les appels
    HTTP sont écrits selon la documentation officielle PayPal Orders v2 / Webhooks,
    à valider avec de vraies clés avant mise en production."""

    nom = "paypal"

    def _get_access_token(self) -> str:
        response = httpx.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    def creer_commande(self, montant: float, devise: str, reference: str, description: str) -> PaymentOrder:
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": reference,
                "description": description,
                "amount": {"currency_code": devise, "value": f"{montant:.2f}"},
            }],
            "application_context": {
                "return_url": PAYMENT_RETURN_URL,
                "cancel_url": PAYMENT_CANCEL_URL,
                "user_action": "PAY_NOW",
            },
        }
        response = httpx.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders",
            json=payload, headers=self._headers(), timeout=15
        )
        response.raise_for_status()
        data = response.json()

        approval_url = next(
            (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"),
            None
        )
        return PaymentOrder(
            order_id=data["id"], approval_url=approval_url, statut=data["status"],
            montant=montant, devise=devise, raw=data,
        )

    def capturer_commande(self, order_id: str) -> PaymentOrder:
        response = httpx.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers=self._headers(), timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        capture = data["purchase_units"][0]["payments"]["captures"][0]
        return PaymentOrder(
            order_id=data["id"], approval_url=None, statut=data["status"],
            montant=float(capture["amount"]["value"]), devise=capture["amount"]["currency_code"],
            raw=data,
        )

    def verifier_webhook(self, headers: dict, raw_body: bytes) -> dict | None:
        body = json.loads(raw_body)

        verify_payload = {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": PAYPAL_WEBHOOK_ID,
            "webhook_event": body,
        }
        response = httpx.post(
            f"{PAYPAL_API_BASE}/v1/notifications/verify-webhook-signature",
            json=verify_payload, headers=self._headers(), timeout=15,
        )
        response.raise_for_status()

        if response.json().get("verification_status") == "SUCCESS":
            return body
        return None
