import httpx

from params import CARTE_API_BASE, CARTE_API_KEY
from services.in_person_gateway.base import InPersonGateway, PaymentResult


class CarteGateway(InPersonGateway):
    """Validation d'un paiement par carte bancaire en caisse via un terminal/passerelle
    de paiement distant (API REST générique façon Stripe Terminal / Adyen). ⚠️ Non testée
    contre un vrai fournisseur dans cet environnement de développement (pas de terminal
    de paiement ni d'identifiants réels disponibles) — les appels HTTP sont écrits selon
    le schéma REST standard de ce type d'API (créer une intention de paiement, capturer,
    rembourser), à valider avec un vrai contrat fournisseur avant mise en production."""

    nom = "carte"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {CARTE_API_KEY}", "Content-Type": "application/json"}

    def valider_paiement(self, montant: float, devise: str, reference_client: str, metadata: dict) -> PaymentResult:
        response = httpx.post(
            f"{CARTE_API_BASE}/payment_intents",
            json={
                "amount": round(montant * 100),  # unités mineures (centimes)
                "currency": devise.lower(),
                "reference": reference_client,
                "capture_method": "automatic",
                "metadata": metadata,
            },
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        succes = data.get("status") in ("succeeded", "captured")
        return PaymentResult(succes=succes, reference=data.get("id"), statut=data.get("status", "inconnu"), raw=data)

    def rembourser(self, reference_transaction: str, montant: float) -> PaymentResult:
        response = httpx.post(
            f"{CARTE_API_BASE}/refunds",
            json={"payment_intent": reference_transaction, "amount": round(montant * 100)},
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        succes = data.get("status") in ("succeeded", "completed")
        return PaymentResult(succes=succes, reference=data.get("id"), statut=data.get("status", "inconnu"), raw=data)
