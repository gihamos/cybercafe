import re
from datetime import datetime

from librouteros import connect
from librouteros.query import Key

from params import MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASSWORD, MIKROTIK_PORT
from services.router_gateway.base import RouterGateway, ConsommationReseau, ActiviteDns

# Formats usuels des lignes de log DNS (paquet « dns » activé via
# `/system logging add topics=dns action=memory`, hors du périmètre de ce pilote) :
# "query from 192.168.88.10: #45473 example.com. type=A cache-answer" (ou variantes
# proches selon la version de RouterOS). Volontairement permissif (IP puis premier nom
# de domaine plausible sur la ligne) plutôt qu'un format figé, non vérifié contre un
# vrai routeur — voir docstring de la classe.
_RE_DNS_LOG = re.compile(
    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*?(?P<domaine>(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63})\.?"
)


class MikrotikGateway(RouterGateway):
    """Pilote pour routeur MikroTik (RouterOS), via l'API native du routeur
    (bibliothèque `librouteros`, port 8728 par défaut). Mécanisme utilisé :

    - Autorisation d'accès WiFi (MAC) : liste de contrôle d'accès sans-fil
      `/interface/wireless/access-list` — le seul mécanisme réellement fiable pour
      bloquer/autoriser un appareil WiFi, car il agit au niveau de l'association
      radio (le client ne peut même pas rejoindre le réseau si son adresse MAC n'est
      pas autorisée), indépendamment de l'IP qui lui sera ensuite attribuée par DHCP.
      Modèle « liste blanche » : ce pilote ajoute une entrée {mac, authentication=yes}
      par client autorisé ; l'interface sans-fil doit être configurée une fois,
      manuellement, avec `default-authentication=no` (hors du périmètre de ce
      pilote) pour que seules les adresses listées ici puissent s'associer.
    - Autorisation d'accès filaire / forwarding (IP) : liste d'adresses
      `/ip/firewall/address-list` — ce pilote ajoute/retire uniquement les membres
      de la liste ; la règle de pare-feu qui n'autorise le trafic sortant QUE pour
      les adresses de cette liste doit être configurée une fois, manuellement, sur
      le routeur (hors du périmètre de ce pilote, qui ne fait que gérer
      l'appartenance à la liste).
    - Limite de débit et suivi de consommation : files d'attente simples
      `/queue/simple`, une par IP (RouterOS cible les files par IP/sous-réseau, pas
      par adresse MAC).
    - Blocage de domaines : entrées DNS statiques `/ip/dns/static` pointant vers
      0.0.0.0 — fonctionne quand les clients utilisent le routeur comme serveur DNS
      (configuration par défaut la plus courante en cybercafé).
    - Résolution MAC : table ARP `/ip/arp`.
    - Sites visités (domaines) : journal système filtré sur le topic « dns »
      (`/log/print`) — nécessite qu'une règle de journalisation DNS soit configurée
      une fois, manuellement, sur le routeur (`/system logging add topics=dns
      action=memory`, hors du périmètre de ce pilote). Domaine résolu uniquement, pas
      l'URL/page complète (voir docstring de `ActiviteDns`).

    ⚠️ Non testée contre un vrai routeur MikroTik dans cet environnement de
    développement (aucun matériel disponible) — la construction des requêtes suit la
    documentation officielle de l'API RouterOS et de `librouteros`, à valider avec un
    vrai routeur avant mise en production. La liste de contrôle d'accès sans-fil
    utilise la syntaxe historique du paquet « wireless » (RouterOS 6 / cAP-hAP
    classiques) ; les routeurs sous le nouveau paquet « wifi » (RouterOS 7) exposent
    l'équivalent sous `/interface/wifi/access-list` et nécessiteraient un pilote (ou
    une variante) dédié. ⚠️ Le parsing du journal DNS (`lister_activite_dns`) est la
    partie la moins fiable de ce pilote : le format exact des lignes de log et de
    l'horodatage varie selon la version de RouterOS et n'a pas pu être vérifié ici —
    à valider et ajuster en priorité contre un vrai routeur."""

    nom = "mikrotik"

    ADDRESS_LIST = "cybercafe-autorises"
    QUEUE_PREFIX = "cybercafe-"
    DNS_COMMENT = "cybercafe:bloque"
    WIFI_COMMENT = "cybercafe:auto"

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

    def autoriser_acces(
        self, mac: str | None, ip: str | None,
        download_kbps: int | None = None, upload_kbps: int | None = None,
    ) -> None:
        api = self._connect()
        try:
            if mac:
                access_list = api.path("/interface/wireless/access-list")
                existant = list(access_list.select(Key("id")).where(Key("mac-address") == mac))
                if existant:
                    access_list.update(**{".id": existant[0]["id"], "authentication": "yes"})
                else:
                    access_list.add(**{"mac-address": mac, "authentication": "yes", "comment": self.WIFI_COMMENT})

            if ip:
                adresses = api.path("/ip/firewall/address-list")
                existant = list(adresses.select(Key("id")).where(Key("address") == ip, Key("list") == self.ADDRESS_LIST))
                if not existant:
                    adresses.add(address=ip, list=self.ADDRESS_LIST, comment="cybercafe:auto")
        finally:
            api.close()

        if ip and (download_kbps or upload_kbps):
            self.definir_limite_debit(mac, ip, download_kbps, upload_kbps)

    def revoquer_acces(self, mac: str | None, ip: str | None) -> None:
        api = self._connect()
        try:
            if mac:
                access_list = api.path("/interface/wireless/access-list")
                for entree in list(access_list.select(Key("id")).where(Key("mac-address") == mac, Key("comment") == self.WIFI_COMMENT)):
                    access_list.remove(entree["id"])

            if ip:
                adresses = api.path("/ip/firewall/address-list")
                for entree in list(adresses.select(Key("id")).where(Key("address") == ip, Key("list") == self.ADDRESS_LIST)):
                    adresses.remove(entree["id"])

                queues = api.path("/queue/simple")
                nom_queue = f"{self.QUEUE_PREFIX}{ip}"
                for entree in list(queues.select(Key("id")).where(Key("name") == nom_queue)):
                    queues.remove(entree["id"])
        finally:
            api.close()

    def definir_limite_debit(self, mac: str | None, ip: str | None, download_kbps: int | None, upload_kbps: int | None) -> None:
        if not ip:
            return  # les files d'attente RouterOS ciblent une IP, pas une adresse MAC
        api = self._connect()
        try:
            queues = api.path("/queue/simple")
            nom_queue = f"{self.QUEUE_PREFIX}{ip}"
            existant = list(queues.select(Key("id")).where(Key("name") == nom_queue))
            max_limit = self._limite_max(download_kbps, upload_kbps)
            if existant:
                queues.update(**{".id": existant[0]["id"], "max-limit": max_limit})
            else:
                queues.add(name=nom_queue, target=ip, **{"max-limit": max_limit})
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

    def get_consommation(self, mac: str | None, ip: str | None) -> ConsommationReseau | None:
        if not ip:
            return None
        api = self._connect()
        try:
            queues = api.path("/queue/simple")
            nom_queue = f"{self.QUEUE_PREFIX}{ip}"
            existant = list(queues.select(Key("bytes")).where(Key("name") == nom_queue))
            if not existant or "bytes" not in existant[0]:
                return None
            # RouterOS renvoie "upload/download" cumulés depuis la création de la queue
            upload_o, download_o = (int(v) for v in str(existant[0]["bytes"]).split("/"))
            return ConsommationReseau(download_mo=download_o / (1024 * 1024), upload_mo=upload_o / (1024 * 1024))
        finally:
            api.close()

    @staticmethod
    def _parse_heure_log(brut: str) -> datetime:
        """Best-effort : formats usuels "jul/14/2026 10:15:23" (entrée ancienne) ou
        "10:15:23" (aujourd'hui). Retombe sur l'heure actuelle si le format ne
        correspond à rien de connu — mieux vaut une entrée légèrement décalée dans le
        temps qu'une exception qui ferait échouer tout le cycle d'ingestion."""
        maintenant = datetime.utcnow()
        try:
            if "/" in brut:
                return datetime.strptime(brut, "%b/%d/%Y %H:%M:%S")
            heure = datetime.strptime(brut, "%H:%M:%S").time()
            return datetime.combine(maintenant.date(), heure)
        except ValueError:
            return maintenant

    def lister_activite_dns(self) -> list[ActiviteDns]:
        # Filtré côté Python plutôt que via `.where(Key("topics") == "dns")` : RouterOS
        # combine souvent plusieurs topics sur une même entrée (ex: "dns,packet"), ce
        # qu'une égalité stricte ne matcherait jamais.
        api = self._connect()
        try:
            entrees = list(api.path("/log").select(Key("time"), Key("topics"), Key("message")))
        finally:
            api.close()

        resultats = []
        for e in entrees:
            if "dns" not in str(e.get("topics", "")):
                continue
            message = str(e.get("message", ""))
            correspondance = _RE_DNS_LOG.search(message)
            if not correspondance:
                continue
            resultats.append(ActiviteDns(
                ip=correspondance.group("ip"),
                domaine=correspondance.group("domaine").rstrip("."),
                horodatage=self._parse_heure_log(str(e.get("time", ""))),
            ))
        return resultats
