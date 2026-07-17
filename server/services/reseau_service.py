from sqlalchemy.orm import Session

from models.session import Session as SessionModel
from models.site_regle import SiteRegle
from params import ROUTER_GATEWAY
from services.bande_passante_service import BandePassanteService
from services.router_gateway import get_router_gateway
from utils.logger import logger


class ReseauService:
    """Fait le lien entre le cycle de vie d'une session (démarrage/fin, changement de
    profil de bande passante, mise à jour des sites bloqués) et le routeur réel — voir
    services/router_gateway/. Best-effort : une panne du routeur ne doit jamais
    empêcher une session de démarrer/se terminer côté application (le client reste
    fonctionnel), l'erreur est seulement journalisée."""

    @staticmethod
    def _identifiants(session: SessionModel) -> tuple[str | None, str | None]:
        """(mac, ip) connus pour cette session — un pilote réseau peut avoir besoin
        des deux à la fois : la MAC pour bloquer/autoriser l'association WiFi de
        façon fiable (indépendante du bail DHCP), l'IP pour la limitation de débit et
        le forwarding pare-feu. Pour un poste kiosque, la MAC vient de sa fiche
        (connue à l'avance) ; pour une session WiFi, elle est résolue via le routeur
        au moment de la connexion (voir resoudre_mac_depuis_ip)."""
        mac = session.mac_client or (session.poste.mac_adresse if session.poste else None)
        ip = session.ip_client or (session.poste.ip if session.poste else None)
        return mac, ip

    @staticmethod
    def resoudre_mac_depuis_ip(ip: str) -> str | None:
        """À appeler à la connexion WiFi (portail) pour tenter de résoudre la MAC de
        l'appareil à partir de son IP, via la table ARP du routeur — best-effort,
        None si le pilote actif ne le supporte pas ou si le routeur ne connaît pas
        encore cette IP."""
        try:
            return get_router_gateway(ROUTER_GATEWAY).resoudre_mac(ip)
        except Exception as e:
            logger.warning(f"[reseau] résolution MAC impossible pour {ip} : {e}")
            return None

    @staticmethod
    def _limite_kbps(db: Session, session: SessionModel) -> tuple[int | None, int | None]:
        profil = BandePassanteService.get_profil_applicable(
            db,
            user_id=session.user_id,
            ticket_id=session.ticket_id,
            poste_id=session.poste_id,
            abonnement_id=session.abonnement_id,
            groupe_id=None,
        )
        if not profil:
            return None, None
        download_kbps = int(profil.download_mbps * 1000) if profil.download_mbps else None
        upload_kbps = int(profil.upload_mbps * 1000) if profil.upload_mbps else None
        return download_kbps, upload_kbps

    @staticmethod
    def autoriser(db: Session, session: SessionModel) -> None:
        """Accorde l'accès internet réel pour cette session (à appeler juste après son
        démarrage). Sans MAC ni IP connue (WiFi non résolu), on ne peut rien faire au
        niveau routeur — la session reste fonctionnelle côté application, seul le
        contrôle réseau réel est indisponible pour ce client."""
        mac, ip = ReseauService._identifiants(session)
        if not mac and not ip:
            logger.warning(f"[reseau] aucun identifiant réseau pour la session {session.id} — accès non contrôlé au niveau routeur")
            return

        download_kbps, upload_kbps = ReseauService._limite_kbps(db, session)
        try:
            get_router_gateway(ROUTER_GATEWAY).autoriser_acces(mac, ip, download_kbps, upload_kbps)
            session.acces_reseau_actif = True
            db.commit()
        except Exception as e:
            logger.error(f"[reseau] échec autorisation pour mac={mac} ip={ip} (session {session.id}) : {e}")

    @staticmethod
    def revoquer(db: Session, session: SessionModel) -> None:
        """Coupe l'accès internet réel de cette session (fin normale, expiration,
        déconnexion). Appelé même si l'autorisation initiale avait échoué, au cas où
        le routeur aurait quand même une entrée résiduelle à nettoyer."""
        mac, ip = ReseauService._identifiants(session)
        if not mac and not ip:
            return
        try:
            get_router_gateway(ROUTER_GATEWAY).revoquer_acces(mac, ip)
        except Exception as e:
            logger.error(f"[reseau] échec révocation pour mac={mac} ip={ip} (session {session.id}) : {e}")
        finally:
            session.acces_reseau_actif = False
            db.commit()

    @staticmethod
    def appliquer_limite_debit(db: Session, session: SessionModel) -> None:
        """À rappeler quand le profil de bande passante applicable a pu changer
        (ex: bascule vers une autre offre/groupe) sur une session déjà autorisée."""
        mac, ip = ReseauService._identifiants(session)
        if (not mac and not ip) or not session.acces_reseau_actif:
            return
        download_kbps, upload_kbps = ReseauService._limite_kbps(db, session)
        try:
            get_router_gateway(ROUTER_GATEWAY).definir_limite_debit(mac, ip, download_kbps, upload_kbps)
        except Exception as e:
            logger.error(f"[reseau] échec mise à jour du débit pour mac={mac} ip={ip} : {e}")

    @staticmethod
    def actualiser_consommation(db: Session, session: SessionModel) -> None:
        """Relit la consommation data réelle constatée par le routeur pour cette
        session et la reporte sur `session.consommation_data_mo` (valeur absolue,
        pas un delta — voir SessionService.definir_consommation_data). Best-effort :
        certains pilotes (simulated, ou un pilote sans compteur par client) renvoient
        toujours None, auquel cas on ne touche à rien.

        Applique aussi le plafond PARTAGÉ entre toutes les sessions actives d'un même
        ticket data : le compteur compte l'ensemble de leur consommation cumulée, pas
        chacune indépendamment — si plusieurs sessions simultanées partagent un même
        ticket (voir la limite de connexions simultanées), dépasser à elles toutes le
        quota du ticket ferme TOUTES ces sessions, pas seulement celle qui vient
        d'être sondée."""
        mac, ip = ReseauService._identifiants(session)
        if not mac and not ip:
            return
        try:
            conso = get_router_gateway(ROUTER_GATEWAY).get_consommation(mac, ip)
        except Exception as e:
            logger.error(f"[reseau] échec lecture de consommation pour mac={mac} ip={ip} (session {session.id}) : {e}")
            return
        if conso is None:
            return

        from services.session_service import SessionService
        SessionService.definir_consommation_data(db, session.id, conso.download_mo + conso.upload_mo)

        if session.ticket_id and session.ticket and session.ticket.restant_data_mo is not None:
            from services.portail_service import PortailService
            actives = PortailService.sessions_actives(db, ticket_id=session.ticket_id)
            total = sum(s.consommation_data_mo or 0 for s in actives)
            if total >= session.ticket.restant_data_mo:
                for s in actives:
                    if s.est_active:
                        SessionService.fermer_session(db, s.id)

    @staticmethod
    def synchroniser_sites_bloques(db: Session) -> None:
        """Pousse la liste globale des domaines actuellement bloqués vers le routeur
        (blocage DNS) — à appeler après toute création/modification/suppression de
        règle. Complémentaire au blocage côté poste (fichier hosts) : c'est le seul
        mécanisme qui protège aussi les clients WiFi, qui n'ont pas d'application
        cybercafe installée sur leur propre appareil."""
        domaines = sorted({r.domaine for r in db.query(SiteRegle).filter(SiteRegle.actif == True).all()})
        try:
            get_router_gateway(ROUTER_GATEWAY).bloquer_domaines(domaines)
        except Exception as e:
            logger.error(f"[reseau] échec synchronisation des sites bloqués : {e}")
