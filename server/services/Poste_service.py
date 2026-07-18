import secrets
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.poste import Poste, PosteEtat
from models.session import Session as SessionModel
from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from models.notification import TypeNotification
from utils.security import generate_temp_password, hash_password
from websocket.manager import manager

CODE_SECOURS_VALIDITE_MINUTES = 20


def _serialize_session_brief(session) -> dict | None:
    if not session:
        return None
    return {
        "id": session.id,
        "user_id": session.user_id,
        "ticket_id": session.ticket_id,
        "limite_minutes": session.limite_minutes,
        "consommation_minutes": session.consommation_minutes,
        "limite_data_mo": session.limite_data_mo,
        "consommation_data_mo": session.consommation_data_mo,
    }


def _serialize_poste_for_admin(poste: Poste) -> dict:
    session_active = next((s for s in poste.sessions if s.est_active), None)
    return {
        "id": poste.id,
        "nom": poste.nom,
        "etat": poste.etat,
        "est_verrouille": poste.est_verrouille,
        "est_en_ligne": poste.est_en_ligne,
        "derniere_activite": poste.derniere_activite.isoformat() if poste.derniere_activite else None,
        "session_active": _serialize_session_brief(session_active),
    }


class PosteService:

    # ---------------------------------------------------------
    # 1. CRÉER UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def creer_poste(
        db: Session,
        nom: str,
        description: str | None = None,
        type_poste=None,
        ip: str | None = None,
        mac_adresse: str | None = None,
        hostname: str | None = None,
        os: str | None = None
    ):
        poste = Poste(
            nom=nom,
            description=description,
            type_poste=type_poste,
            ip=ip,
            mac_adresse=mac_adresse,
            hostname=hostname,
            os=os,
            etat=PosteEtat.BLOQUE,
            est_verrouille=True,
            est_en_ligne=False,
            derniere_activite=datetime.utcnow(),
            token=secrets.token_urlsafe(32)
        )

        db.add(poste)
        db.commit()
        db.refresh(poste)

        HistoriqueService.log(
            db=db,
            type_evenement="poste_create",
            description=f"Création du poste {nom}",
            poste_id=poste.id
        )

        return poste

    # ---------------------------------------------------------
    # 1bis. METTRE À JOUR UN POSTE (champs génériques)
    # ---------------------------------------------------------
    @staticmethod
    def mettre_a_jour_poste(db: Session, poste_id: int, data: dict):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        for key, value in data.items():
            if hasattr(poste, key) and value is not None:
                setattr(poste, key, value)

        db.commit()
        db.refresh(poste)

        HistoriqueService.log(
            db=db,
            type_evenement="poste_update",
            description=f"Modification du poste {poste.nom}",
            poste_id=poste_id,
            details=data
        )

        return poste

    # ---------------------------------------------------------
    # 1ter. RÉGÉNÉRER LE TOKEN DU POSTE (client desktop)
    # ---------------------------------------------------------
    @staticmethod
    def regenerer_token(db: Session, poste_id: int):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        poste.token = secrets.token_urlsafe(32)
        db.commit()
        db.refresh(poste)

        HistoriqueService.log(
            db=db,
            type_evenement="poste_update",
            description=f"Token régénéré pour le poste {poste.nom}",
            poste_id=poste_id
        )

        return poste

    # ---------------------------------------------------------
    # AUTHENTIFIER UN POSTE PAR SON TOKEN (client desktop)
    # ---------------------------------------------------------
    @staticmethod
    def authentifier_par_token(db: Session, poste_id: int, token: str):
        poste = db.query(Poste).get(poste_id)
        if not poste or not poste.token or poste.token != token:
            return None
        return poste

    # ---------------------------------------------------------
    # 2. VERROUILLER UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def verrouiller_poste(db: Session, poste_id: int):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        poste.est_verrouille = True
        poste.etat = PosteEtat.BLOQUE
        db.commit()

        manager.send_to_poste_threadsafe(poste_id, "lock")
        manager.broadcast_to_admins_threadsafe("poste_updated", _serialize_poste_for_admin(poste))

        HistoriqueService.log(
            db=db,
            type_evenement="poste_lock",
            description=f"Poste {poste.nom} verrouillé",
            poste_id=poste_id
        )

        return poste

    # ---------------------------------------------------------
    # 3. DÉVERROUILLER UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def deverrouiller_poste(db: Session, poste_id: int):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        poste.est_verrouille = False

        # Si pas occupé → état = libre
        if poste.etat != PosteEtat.OCCUPE:
            poste.etat = PosteEtat.LIBRE

        db.commit()

        manager.send_to_poste_threadsafe(poste_id, "unlock")
        manager.broadcast_to_admins_threadsafe("poste_updated", _serialize_poste_for_admin(poste))

        HistoriqueService.log(
            db=db,
            type_evenement="poste_unlock",
            description=f"Poste {poste.nom} déverrouillé",
            poste_id=poste_id
        )

        return poste

    # ---------------------------------------------------------
    # 4. OCCUPER UN POSTE (session démarre)
    # ---------------------------------------------------------
    @staticmethod
    def occuper_poste(db: Session, poste_id: int):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        if poste.etat == PosteEtat.OCCUPE:
            raise ValueError("Poste déjà occupé")

        poste.etat = PosteEtat.OCCUPE
        poste.est_verrouille = False
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="poste_occupy",
            description=f"Poste {poste.nom} occupé",
            poste_id=poste_id
        )

        return poste

    # ---------------------------------------------------------
    # 5. LIBÉRER UN POSTE (session terminée)
    # ---------------------------------------------------------
    @staticmethod
    def liberer_poste(db: Session, poste_id: int):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        poste.etat = PosteEtat.LIBRE
        poste.est_verrouille = True  # sécurité
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="poste_free",
            description=f"Poste {poste.nom} libéré",
            poste_id=poste_id
        )

        return poste

    # ---------------------------------------------------------
    # 6. HEARTBEAT (ping du poste)
    # ---------------------------------------------------------
    @staticmethod
    def heartbeat(
        db: Session, poste_id: int, version_client: str | None = None,
        ip: str | None = None, mac_adresse: str | None = None,
    ):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        etait_hors_ligne = not poste.est_en_ligne

        poste.derniere_activite = datetime.utcnow()
        poste.est_en_ligne = True

        # Si le poste était hors ligne → repasser en libre ou occupé
        if poste.etat == PosteEtat.HORS_LIGNE:
            poste.etat = PosteEtat.LIBRE if not poste.est_verrouille else PosteEtat.BLOQUE

        if version_client:
            poste.version_client = version_client

        # ip/mac_adresse sont uniques en base : on ne les met à jour que s'ils ne
        # sont pas déjà pris par un autre poste (adresse IP réattribuée par le
        # routeur, carte réseau partagée entre deux machines, etc.) — sinon on
        # garde la valeur existante plutôt que de faire échouer le heartbeat.
        if ip and poste.ip != ip and not db.query(Poste).filter(Poste.ip == ip, Poste.id != poste.id).first():
            poste.ip = ip
        if (
            mac_adresse and poste.mac_adresse != mac_adresse
            and not db.query(Poste).filter(Poste.mac_adresse == mac_adresse, Poste.id != poste.id).first()
        ):
            poste.mac_adresse = mac_adresse

        db.commit()

        if etait_hors_ligne:
            manager.broadcast_to_admins_threadsafe("poste_updated", _serialize_poste_for_admin(poste))

        return poste

    # ---------------------------------------------------------
    # 7. DÉTECTER LES POSTES HORS LIGNE
    # ---------------------------------------------------------
    @staticmethod
    def verifier_postes_hors_ligne(db: Session, timeout_seconds: int = 30):
        now = datetime.utcnow()
        seuil = now - timedelta(seconds=timeout_seconds)

        postes = db.query(Poste).all()
        hors_ligne = []

        for p in postes:
            if p.derniere_activite < seuil:
                if p.etat != PosteEtat.HORS_LIGNE:
                    p.etat = PosteEtat.HORS_LIGNE
                    p.est_en_ligne = False
                    hors_ligne.append(p)

        db.commit()

        for p in hors_ligne:
            manager.broadcast_to_admins_threadsafe("poste_updated", _serialize_poste_for_admin(p))

        return hors_ligne

    # ---------------------------------------------------------
    # 8. ENVOYER UNE COMMANDE AU POSTE
    # ---------------------------------------------------------
    @staticmethod
    def envoyer_commande(db: Session, poste_id: int, commande: str, details: dict | None = None):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        manager.send_to_poste_threadsafe(poste_id, "commande", {"commande": commande, "details": details})

        HistoriqueService.log(
            db=db,
            type_evenement="poste_command",
            description=f"Commande envoyée au poste {poste.nom}: {commande}",
            poste_id=poste_id,
            details=details
        )

        return {"status": "commande envoyée" if manager.is_connected(poste_id) else "poste hors ligne, commande non délivrée"}

    # ---------------------------------------------------------
    # 8bis. DÉSACTIVER LE KIOSK À DISTANCE
    # ---------------------------------------------------------
    @staticmethod
    def desactiver_kiosque(db: Session, poste_id: int):
        """Envoie une commande de désactivation au client kiosk (voir client/main.py
        ::_on_message, type "disable_kiosk") : le client ferme immédiatement le
        kiosk, sans re-demander de confirmation locale (déjà autorisé par le rôle
        + la permission "postes" côté serveur, voir router/poste.py)."""
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        manager.send_to_poste_threadsafe(poste_id, "disable_kiosk")

        HistoriqueService.log(
            db=db,
            type_evenement="poste_disable_kiosk",
            description=f"Désactivation du kiosk demandée pour le poste {poste.nom}",
            poste_id=poste_id
        )

        return {
            "status": "commande envoyée" if manager.is_connected(poste_id)
            else "poste hors ligne, la commande sera sans effet tant qu'il n'est pas reconnecté"
        }

    # ---------------------------------------------------------
    # 8ter. GÉNÉRER UN CODE DE SECOURS (déverrouillage admin local hors-ligne)
    # ---------------------------------------------------------
    @staticmethod
    def generer_code_secours(db: Session, poste_id: int, validite_minutes: int = CODE_SECOURS_VALIDITE_MINUTES):
        """Génère un code à usage unique que l'opérateur communique par téléphone
        à la personne présente sur le poste, pour le cas où le mot de passe du
        compte admin Windows est oublié — voir client/ui/admin_menu_dialog.py.
        Seul le hash (jamais le code en clair) est stocké et transmis au client :
        le code n'est renvoyé qu'ici, une seule fois, à l'appelant de cet endpoint.
        Poussé immédiatement au client si connecté (voir router/ws_poste.py) pour
        qu'il soit disponible localement même si le poste passe hors-ligne juste
        après — un poste qui n'a jamais reçu le hash avant de perdre la
        connexion ne peut, par nature, pas récupérer un code généré après coup."""
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        code = generate_temp_password()
        expire_le = datetime.utcnow() + timedelta(minutes=validite_minutes)
        poste.code_secours_hash = hash_password(code)
        poste.code_secours_expire_le = expire_le
        db.commit()

        manager.send_to_poste_threadsafe(poste_id, "code_secours", {
            "hash": poste.code_secours_hash,
            "expire_le": expire_le.isoformat(),
        })

        HistoriqueService.log(
            db=db,
            type_evenement="poste_code_secours",
            description=f"Code de secours généré pour le poste {poste.nom}",
            poste_id=poste_id
        )

        return {
            "code": code,
            "expire_le": expire_le.isoformat(),
            "transmis_au_poste": manager.is_connected(poste_id),
        }

    # ---------------------------------------------------------
    # 9. RÉCUPÉRER LA SESSION ACTIVE DU POSTE
    # ---------------------------------------------------------
    @staticmethod
    def get_session_active(db: Session, poste_id: int):
        return (
            db.query(SessionModel)
            .filter(SessionModel.poste_id == poste_id)
            .filter(SessionModel.est_active == True)
            .first()
        )

    # ---------------------------------------------------------
    # 10. SUPPRIMER UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_poste(db: Session, poste_id: int):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        if poste.etat == PosteEtat.OCCUPE:
            raise ValueError("Impossible de supprimer un poste occupé")

        db.delete(poste)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="poste_delete",
            description=f"Poste {poste.nom} supprimé",
            poste_id=poste_id
        )

        return True
