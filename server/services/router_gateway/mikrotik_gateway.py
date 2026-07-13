from librouteros import connect
from librouteros.query import Key

from params import MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASSWORD, MIKROTIK_PORT
from services.router_gateway.base import RouterGateway, ConsommationReseau


class MikrotikGateway(RouterGateway):
    """Pilote pour routeur MikroTik (RouterOS), via l'API native du routeur
    (bibliothèque `librouteros`, port 8728 par défaut). Mécanisme utilisé :

    - Autorisation d'accès : liste d'adresses `/ip/firewall/address-list` — ce
      pilote ajoute/retire uniquement les membres de la liste ; la règle de pare-feu
      qui n'autorise le trafic sortant QUE pour les adresses de cette liste doit être
      configurée une fois, manuellement, sur le routeur (hors du périmètre de ce
      pilote, qui ne fait que gérer l'appartenance à la liste).
    - Limite de débit : files d'attente simples `/queue/simple`, une par client.
    - Blocage de domaines : entrées DNS statiques `/ip/dns/static` pointant vers
      0.0.0.0 — fonctionne quand les clients utilisent le routeur comme serveur DNS
      (configuration par défaut la plus courante en cybercafé).
    - Résolution MAC : table ARP `/ip/arp`.

    ⚠️ Non testée contre un vrai routeur MikroTik dans cet environnement de
    développement (aucun matériel disponible) — la construction des requêtes suit la
    documentation officielle de l'API RouterOS et de `librouteros`, à valider avec un
    vrai routeur avant mise en production."""

    nom = "mikrotik"

    ADDRESS_LIST = "cybercafe-autorises"
    QUEUE_PREFIX = "cybercafe-"
    DNS_COMMENT = "cybercafe:bloque"

    def _connect(self):
        if not MIKROTIK_HOST:
            raise ValueError("MIKROTIK_HOST non configuré")
        try:
            return connect(
                host=MIKROTIK_HOST, username=MIKROTIK_USER, password=MIKROTIK_PASSWORD,
                port=MIKROTIK_PORT, timeout=10,
            )
        except Exception as e:
            raise ValueError(f"Routeur MikroTik injoignable ({MIKROTIK_HOST}:{MIKROTIK_PORT}) : {e}")

    @staticmethod
    def _limite_max(download_kbps: int | None, upload_kbps: int | None) -> str:
        # RouterOS exprime max-limit en upload/download (dans cet ordre), "0" = illimité
        return f"{upload_kbps or 0}k/{download_kbps or 0}k"

    def autoriser_acces(self, identifiant: str, download_kbps: int | None = None, upload_kbps: int | None = None) -> None:
        api = self._connect()
        try:
            adresses = api.path("/ip/firewall/address-list")
            existant = list(adresses.select(Key("id")).where(Key("address") == identifiant, Key("list") == self.ADDRESS_LIST))
            if not existant:
                adresses.add(address=identifiant, list=self.ADDRESS_LIST, comment="cybercafe:auto")
        finally:
            api.close()

        if download_kbps or upload_kbps:
            self.definir_limite_debit(identifiant, download_kbps, upload_kbps)

    def revoquer_acces(self, identifiant: str) -> None:
        api = self._connect()
        try:
            adresses = api.path("/ip/firewall/address-list")
            for entree in list(adresses.select(Key("id")).where(Key("address") == identifiant, Key("list") == self.ADDRESS_LIST)):
                adresses.remove(entree["id"])

            queues = api.path("/queue/simple")
            nom_queue = f"{self.QUEUE_PREFIX}{identifiant}"
            for entree in list(queues.select(Key("id")).where(Key("name") == nom_queue)):
                queues.remove(entree["id"])
        finally:
            api.close()

    def definir_limite_debit(self, identifiant: str, download_kbps: int | None, upload_kbps: int | None) -> None:
        api = self._connect()
        try:
            queues = api.path("/queue/simple")
            nom_queue = f"{self.QUEUE_PREFIX}{identifiant}"
            existant = list(queues.select(Key("id")).where(Key("name") == nom_queue))
            max_limit = self._limite_max(download_kbps, upload_kbps)
            if existant:
                queues.update(**{".id": existant[0]["id"], "max-limit": max_limit})
            else:
                queues.add(name=nom_queue, target=identifiant, **{"max-limit": max_limit})
        finally:
            api.close()

    def bloquer_domaines(self, domaines: list[str]) -> None:
        voulus = set(domaines)
        api = self._connect()
        try:
            dns_static = api.path("/ip/dns/static")
            existants = {
                e["name"]: e["id"]
                for e in dns_static.select(Key("id"), Key("name")).where(Key("comment") == self.DNS_COMMENT)
            }
            for domaine in voulus - existants.keys():
                dns_static.add(name=domaine, address="0.0.0.0", comment=self.DNS_COMMENT)
            for domaine, id_ in existants.items():
                if domaine not in voulus:
                    dns_static.remove(id_)
        finally:
            api.close()

    def resoudre_mac(self, ip: str) -> str | None:
        api = self._connect()
        try:
            arp = list(api.path("/ip/arp").select(Key("mac-address")).where(Key("address") == ip))
            return arp[0].get("mac-address") if arp else None
        finally:
            api.close()

    def get_consommation(self, identifiant: str) -> ConsommationReseau | None:
        api = self._connect()
        try:
            queues = api.path("/queue/simple")
            nom_queue = f"{self.QUEUE_PREFIX}{identifiant}"
            existant = list(queues.select(Key("bytes")).where(Key("name") == nom_queue))
            if not existant or "bytes" not in existant[0]:
                return None
            # RouterOS renvoie "upload/download" cumulés depuis la création de la queue
            upload_o, download_o = (int(v) for v in str(existant[0]["bytes"]).split("/"))
            return ConsommationReseau(download_mo=download_o / (1024 * 1024), upload_mo=upload_o / (1024 * 1024))
        finally:
            api.close()
