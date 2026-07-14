from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConsommationReseau:
    """Volume de données réel constaté par le routeur pour un client — indépendant du
    suivi applicatif (BandePassanteUsage), qui reste alimenté séparément."""

    download_mo: float
    upload_mo: float


@dataclass
class ActiviteDns:
    """Une requête DNS observée par le routeur — le seul niveau de détail réaliste
    pour « les sites visités » par un appareil WiFi qui n'a pas notre application
    installée (contrairement à un poste kiosque, dont l'historique de navigateur
    local donne l'URL complète — voir models/historique_navigation.py). Le nom de
    domaine résolu n'est qu'une approximation du site réellement visité (préchargement,
    traqueurs, notifications en arrière-plan...), mais reste la seule visibilité
    possible sans intercepter le trafic HTTPS lui-même."""

    ip: str
    domaine: str
    horodatage: datetime


class RouterGateway(ABC):
    """Interface commune pour les équipements réseau (routeur MikroTik, box Linux
    faisant office de passerelle, OpenWrt/pfSense...). Toute nouvelle implémentation
    doit fournir ces méthodes pour être branchée sur services/reseau_service.py sans
    rien changer côté appelant — voir router_gateway/__init__.py::get_router_gateway
    pour l'enregistrer.

    Un client réseau est identifié par `mac` et/ou `ip` (les deux optionnels, mais au
    moins un fourni par l'appelant) plutôt qu'un identifiant unique : selon
    l'équipement, le contrôle d'accès WiFi réel se fait au niveau de l'association
    radio (liste de contrôle par adresse MAC — fiable même si l'IP change au
    prochain bail DHCP) tandis que la limitation de débit et le blocage de domaines
    passent presque toujours par l'IP (files d'attente, règles de pare-feu). Un
    pilote qui ne gère qu'un seul des deux axes doit simplement ignorer le paramètre
    qu'il ne sait pas exploiter."""

    nom: str

    @abstractmethod
    def autoriser_acces(
        self,
        mac: str | None,
        ip: str | None,
        download_kbps: int | None = None,
        upload_kbps: int | None = None,
    ) -> None:
        """Accorde l'accès internet à ce client, avec une limite de débit optionnelle
        (aucune limite = illimité, dans les limites du lien internet lui-même)."""
        ...

    @abstractmethod
    def revoquer_acces(self, mac: str | None, ip: str | None) -> None:
        """Coupe l'accès internet de ce client (fin de session, expiration...)."""
        ...

    @abstractmethod
    def definir_limite_debit(
        self,
        mac: str | None,
        ip: str | None,
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

    def get_consommation(self, mac: str | None, ip: str | None) -> ConsommationReseau | None:
        """Volume de données réel consommé par ce client, si le routeur l'expose
        (optionnel : certains pilotes n'ont pas de compteur par client)."""
        return None

    def lister_activite_dns(self) -> list[ActiviteDns]:
        """Requêtes DNS récentes vues par le routeur, tous clients confondus
        (optionnel : certains pilotes n'exposent pas de journal DNS exploitable).
        L'appelant est responsable d'attribuer chaque entrée à un client via son IP
        et de dédupliquer les entrées déjà ingérées."""
        return []
