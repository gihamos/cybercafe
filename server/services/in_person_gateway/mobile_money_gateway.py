import httpx

from params import MOBILE_MONEY_API_BASE, MOBILE_MONEY_API_KEY
from services.in_person_gateway.base import InPersonGateway, PaymentResult


class MobileMoneyGateway(InPersonGateway):
    """Validation d'un paiement mobile money en caisse (le client compose un code USSD
    ou confirme sur son téléphone, l'opérateur saisit la référence de la transaction).
    ⚠️ Non testée contre un vrai fournisseur (Orange Money, MTN MoMo, etc.) dans cet
    environnement de développement — écrite selon le schéma REST générique commun à ces
    API (collecter, vérifier statut, rembourser), à adapter au fournisseur réel retenu
    (chaque opérateur a ses propres champs) avant mise en production."""

    nom = "mobile_money"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {MOBILE_MONEY_API_KEY}", "Content-Type": "application/json"}

    def valider_paiement(self, montant: float, devise: str, reference_client: str, metadata: dict) -> PaymentResult:
        response = httpx.post(
            f"{MOBILE_MONEY_API_BASE}/collections",
            json={
                "amount": montant,
                "currency": devise,
                "externalId": reference_client,
                "payer": metadata.get("numero_telephone"),
            },
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        succes = data.get("status") in ("SUCCESSFUL", "COMPLETED")
        return PaymentResult(succes=succes, reference=data.get("financialTransactionId") or data.get("id"), statut=data.get("status", "inconnu"), raw=data)

    def rembourser(self, reference_transaction: str, montant: float) -> PaymentResult:
        response = httpx.post(
            f"{MOBILE_MONEY_API_BASE}/refunds",
            json={"referenceId": reference_transaction, "amount": montant},
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        succes = data.get("status") in ("SUCCESSFUL", "COMPLETED")
        return PaymentResult(succes=succes, reference=data.get("id"), statut=data.get("status", "inconnu"), raw=data)
