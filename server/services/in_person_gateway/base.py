from abc import ABC, abstractmethod


class PaymentResult:
    """Résultat neutre (indépendant du fournisseur) d'une validation ou d'un
    remboursement de paiement en caisse."""

    def __init__(self, succes: bool, reference: str | None, statut: str, raw: dict | None = None):
        self.succes = succes
        self.reference = reference
        self.statut = statut
        self.raw = raw or {}


class InPersonGateway(ABC):
    """Interface commune pour les moyens de paiement validés en caisse via l'API d'un
    fournisseur (carte bancaire via un terminal/passerelle, mobile money) — contrairement
    à payment_gateway/ (paiement en ligne avec redirection), ici le client est physiquement
    au comptoir et le paiement est validé de façon synchrone.

    Toute nouvelle intégration doit implémenter ces deux méthodes pour être branchée sur
    services/paiement_service.py sans rien changer côté appelant — voir
    in_person_gateway/__init__.py::get_gateway pour l'enregistrer."""

    nom: str

    @abstractmethod
    def valider_paiement(self, montant: float, devise: str, reference_client: str, metadata: dict) -> PaymentResult:
        """Valide un paiement déjà initié physiquement (carte insérée/mobile money
        composé par le client) auprès du fournisseur, retourne le résultat."""
        ...

    @abstractmethod
    def rembourser(self, reference_transaction: str, montant: float) -> PaymentResult:
        """Rembourse une transaction déjà validée par ce fournisseur."""
        ...
