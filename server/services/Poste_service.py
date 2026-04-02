from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.poste import Poste, PosteEtat
from models.session import Session as SessionModel
from server.services.historique_service import HistoriqueService
from server.services.notification_service import NotificationService
from models.notification import TypeNotification


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
        mac: str | None = None,
        hostname: str | None = None,
        os: str | None = None
    ):
        poste = Poste(
            nom=nom,
            description=description,
            type_poste=type_poste,
            ip=ip,
            mac_adresse=mac,
            hostname=hostname,
            os=os,
            etat=PosteEtat.BLOQUE,
            est_verrouille=True,
            est_en_ligne=False,
            derniere_activite=datetime.utcnow()
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
    def heartbeat(db: Session, poste_id: int, version_client: str | None = None):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        poste.derniere_activite = datetime.utcnow()
        poste.est_en_ligne = True

        # Si le poste était hors ligne → repasser en libre ou occupé
        if poste.etat == PosteEtat.HORS_LIGNE:
            poste.etat = PosteEtat.LIBRE if not poste.est_verrouille else PosteEtat.BLOQUE

        if version_client:
            poste.version_client = version_client

        db.commit()
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
        return hors_ligne

    # ---------------------------------------------------------
    # 8. ENVOYER UNE COMMANDE AU POSTE
    # ---------------------------------------------------------
    @staticmethod
    def envoyer_commande(db: Session, poste_id: int, commande: str, details: dict | None = None):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        # Ici tu pourras brancher WebSocket / MQTT / HTTP
        # Pour l’instant on log l’action

        HistoriqueService.log(
            db=db,
            type_evenement="poste_command",
            description=f"Commande envoyée au poste {poste.nom}: {commande}",
            poste_id=poste_id,
            details=details
        )

        return {"status": "commande envoyée"}

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
