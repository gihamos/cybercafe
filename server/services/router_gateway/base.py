from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ConsommationReseau:
    """Volume de données réel constaté par le routeur pour un client — indépendant du
    suivi applicatif (BandePassanteUsage), qui reste alimenté séparément."""

    download_mo: float
    upload_mo: float


class RouterGateway(ABC):
    """Interface commune pour les équipements réseau (routeur MikroTik, box Linux
    faisant office de passerelle, OpenWrt/pfSense...). Toute nouvelle implémentation
    doit fournir ces méthodes pour être branchée sur services/reseau_service.py sans
    rien changer côté appelant — voir router_gateway/__init__.py::get_router_gateway
    pour l'enregistrer.

    `identifiant` désigne le client réseau à contrôler : une adresse MAC de préférence
    (stable même si le bail DHCP change), à défaut une adresse IP."""

    nom: str

    @abstractmethod
    def autoriser_acces(
        self,
        identifiant: str,
        download_kbps: int | None = None,
        upload_kbps: int | None = None,
    ) -> None:
        """Accorde l'accès internet à ce client, avec une limite de débit optionnelle
        (aucune limite = illimité, dans les limites du lien internet lui-même)."""
        ...

    @abstractmethod
    def revoquer_acces(self, identifiant: str) -> None:
        """Coupe l'accès internet de ce client (fin de session, expiration...)."""
        ...

    @abstractmethod
    def definir_limite_debit(
        self,
        identifiant: str,
        download_kbps: int | None,
        upload_kbps: int | None,
    ) -> None:
        """Met à jour la limite de débit d'un client déjà autorisé (ex: changement de
        profil de bande passante en cours de session)."""
        ...

    @abstractmethod
    def bloquer_domaines(self, domaines: list[str]) -> None:
        """Synchronise la liste globale de domaines bloqués (remplace entièrement la
        liste précédemment poussée par ce pilote — les domaines retirés côté
        application sont aussi débloqués côté routeur)."""
        ...

    @abstractmethod
    def resoudre_mac(self, ip: str) -> str | None:
        """Résout l'adresse MAC correspondant à une IP via la table ARP/DHCP du
        routeur — None si inconnue (ex: client jamais vu par ce routeur)."""
        ...

    def get_consommation(self, identifiant: str) -> ConsommationReseau | None:
        """Volume de données réel consommé par ce client, si le routeur l'expose
        (optionnel : certains pilotes n'ont pas de compteur par client)."""
        return None
