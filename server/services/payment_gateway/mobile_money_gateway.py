import json

import httpx

from params import MOBILE_MONEY_API_BASE, MOBILE_MONEY_API_KEY, PAYMENT_RETURN_URL, PAYMENT_CANCEL_URL
from services.payment_gateway.base import PaymentGateway, PaymentOrder


class MobileMoneyEnLigneGateway(PaymentGateway):
    """Paiement par mobile money à distance (portail WiFi) via une passerelle de
    checkout hébergé générique (façon Stripe Checkout / Adyen Pay by Link) : création
    d'une session de paiement → redirection du payeur vers l'URL hébergée →
    confirmation asynchrone par webhook. ⚠️ Non testée contre un vrai fournisseur dans
    cet environnement de développement — appels écrits selon le schéma REST standard de
    ce type d'API, à valider avec un vrai contrat fournisseur avant mise en production.
    Réutilise MOBILE_MONEY_API_BASE / MOBILE_MONEY_API_KEY (params.py), comme la validation carte en
    caisse."""

    nom = "mobile_money"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {MOBILE_MONEY_API_KEY}", "Content-Type": "application/json"}

    def creer_commande(self, montant: float, devise: str, reference: str, description: str) -> PaymentOrder:
        response = httpx.post(
            f"{MOBILE_MONEY_API_BASE}/checkout_sessions",
            json={
                "amount": round(montant * 100),
                "currency": devise.lower(),
                "reference": reference,
                "description": description,
                "success_url": PAYMENT_RETURN_URL,
                "cancel_url": PAYMENT_CANCEL_URL,
            },
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return PaymentOrder(
            order_id=data["id"],
            approval_url=data.get("url"),
            statut=data.get("status", "created"),
            montant=montant,
            devise=devise,
            raw=data,
        )

    def capturer_commande(self, order_id: str) -> PaymentOrder:
        response = httpx.post(
            f"{MOBILE_MONEY_API_BASE}/checkout_sessions/{order_id}/capture",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        statut = "COMPLETED" if data.get("status") in ("succeeded", "captured", "complete") else data.get("status", "inconnu")
        return PaymentOrder(
            order_id=order_id, approval_url=None, statut=statut,
            montant=(data.get("amount") or 0) / 100, devise=(data.get("currency") or "eur").upper(), raw=data,
        )

    def verifier_webhook(self, headers: dict, raw_body: bytes) -> dict | None:
        # Vérification de signature propre au fournisseur (en-tête HMAC standard) ; à
        # brancher sur le mécanisme réel du contrat retenu.
        if not headers.get("x-signature"):
            return None
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            return None
