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
    def _identifiant(session: SessionModel) -> str | None:
        """MAC de préférence (stable), IP à défaut — la MAC d'un poste kiosque est
        connue à l'avance (fiche poste) ; pour une session WiFi, elle est résolue via
        le routeur au moment de la connexion (voir _resoudre_identifiant_wifi)."""
        if session.mac_client:
            return session.mac_client
        if session.poste and session.poste.mac_adresse:
            return session.poste.mac_adresse
        if session.ip_client:
            return session.ip_client
        if session.poste and session.poste.ip:
            return session.poste.ip
        return None

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
        démarrage). Sans identifiant réseau connu (WiFi sans MAC/IP résolue), on ne
        peut rien faire au niveau routeur — la session reste fonctionnelle côté
        application, seul le contrôle réseau réel est indisponible pour ce client."""
        identifiant = ReseauService._identifiant(session)
        if not identifiant:
            logger.warning(f"[reseau] aucun identifiant réseau pour la session {session.id} — accès non contrôlé au niveau routeur")
            return

        download_kbps, upload_kbps = ReseauService._limite_kbps(db, session)
        try:
            get_router_gateway(ROUTER_GATEWAY).autoriser_acces(identifiant, download_kbps, upload_kbps)
            session.acces_reseau_actif = True
            db.commit()
        except Exception as e:
            logger.error(f"[reseau] échec autorisation pour {identifiant} (session {session.id}) : {e}")

    @staticmethod
    def revoquer(db: Session, session: SessionModel) -> None:
        """Coupe l'accès internet réel de cette session (fin normale, expiration,
        déconnexion). Appelé même si l'autorisation initiale avait échoué, au cas où
        le routeur aurait quand même une entrée résiduelle à nettoyer."""
        identifiant = ReseauService._identifiant(session)
        if not identifiant:
            return
        try:
            get_router_gateway(ROUTER_GATEWAY).revoquer_acces(identifiant)
        except Exception as e:
            logger.error(f"[reseau] échec révocation pour {identifiant} (session {session.id}) : {e}")
        finally:
            session.acces_reseau_actif = False
            db.commit()

    @staticmethod
    def appliquer_limite_debit(db: Session, session: SessionModel) -> None:
        """À rappeler quand le profil de bande passante applicable a pu changer
        (ex: bascule vers une autre offre/groupe) sur une session déjà autorisée."""
        identifiant = ReseauService._identifiant(session)
        if not identifiant or not session.acces_reseau_actif:
            return
        download_kbps, upload_kbps = ReseauService._limite_kbps(db, session)
        try:
            get_router_gateway(ROUTER_GATEWAY).definir_limite_debit(identifiant, download_kbps, upload_kbps)
        except Exception as e:
            logger.error(f"[reseau] échec mise à jour du débit pour {identifiant} : {e}")

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
