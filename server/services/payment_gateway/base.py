from abc import ABC, abstractmethod


class PaymentOrder:
    """Représentation neutre (indépendante de la passerelle) d'une commande de
    paiement, retournée par toutes les implémentations de PaymentGateway."""

    def __init__(self, order_id: str, approval_url: str | None, statut: str, montant: float, devise: str, raw: dict):
        self.order_id = order_id
        self.approval_url = approval_url
        self.statut = statut
        self.montant = montant
        self.devise = devise
        self.raw = raw


class PaymentGateway(ABC):
    """Interface commune pour les passerelles de paiement en ligne (PayPal, Stripe...).
    Toute nouvelle passerelle doit implémenter ces trois méthodes pour être branchée
    sur services/paiement_service.py sans rien changer côté appelant — voir
    payment_gateway/__init__.py::get_gateway pour l'enregistrer."""

    nom: str

    @abstractmethod
    def creer_commande(self, montant: float, devise: str, reference: str, description: str) -> PaymentOrder:
        """Crée une commande côté passerelle, retourne l'ID externe + l'URL d'approbation
        (l'URL à ouvrir/partager avec le payeur pour qu'il valide le paiement)."""
        ...

    @abstractmethod
    def capturer_commande(self, order_id: str) -> PaymentOrder:
        """Finalise l'encaissement d'une commande déjà approuvée par le payeur."""
        ...

    @abstractmethod
    def verifier_webhook(self, headers: dict, raw_body: bytes) -> dict | None:
        """Valide l'authenticité d'un webhook entrant (signature), retourne l'événement
        parsé si valide, None sinon."""
        ...
