from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from models.poste import Poste
from models.ticket import Ticket, TypeTicket
from models.user import User, is_validUser
from models.pay_connect_request import PayConnectRequest, StatutPayConnect
from models.paiement import TypePaiement
from services.session_service import SessionService
from services.paiement_service import PaiementService
from services.system_setting_service import SystemSettingsService
from services.historique_service import HistoriqueService
from utils.security import verify_password
from websocket.manager import manager

TARIFS_DEFAUT = [
    {"minutes": 30, "prix": 1.0},
    {"minutes": 60, "prix": 1.8},
    {"minutes": 120, "prix": 3.0},
]


class PayConnectService:

    @staticmethod
    def lister_tarifs(db: Session) -> list[dict]:
        try:
            return SystemSettingsService.get_valeur(db, "pay_and_connect.tarifs")
        except ValueError:
            return TARIFS_DEFAUT

    @staticmethod
    def _prix_pour(db: Session, minutes: int) -> float:
        tarif = next((t for t in PayConnectService.lister_tarifs(db) if int(t["minutes"]) == int(minutes)), None)
        if not tarif:
            raise ValueError("Durée non proposée par le tarif Pay & Connect")
        return float(tarif["prix"])

    @staticmethod
    def _verifier_poste_disponible(db: Session, poste_id: int) -> Poste:
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")
        if not poste.est_en_ligne:
            raise ValueError("Le poste est hors ligne")
        if db.query(PayConnectRequest).filter(
            PayConnectRequest.poste_id == poste_id, PayConnectRequest.statut == StatutPayConnect.EN_ATTENTE
        ).first():
            raise ValueError("Une demande Pay & Connect est déjà en attente sur ce poste")
        return poste

    # ---------------------------------------------------------
    # Connexion instantanée via solde de compte
    # ---------------------------------------------------------
    @staticmethod
    def demarrer_avec_solde(db: Session, poste_id: int, username: str, password: str, minutes: int):
        PayConnectService._verifier_poste_disponible(db, poste_id)

        user = db.query(User).filter(User.username == username).first()
        if user is None or not password or not verify_password(password, user.password):
            raise ValueError("Identifiants incorrects")

        validuser = is_validUser(user)
        if not validuser["valide"]:
            raise ValueError(validuser["detail"])

        montant = PayConnectService._prix_pour(db, minutes)
        if user.solde_euros < montant:
            raise ValueError("Solde insuffisant")

        PaiementService.payer_via_solde(db, user.id, montant)

        session = SessionService.demarrer_session(
            db=db, poste_id=poste_id, user_id=user.id, limite_minutes_override=minutes
        )

        HistoriqueService.log(
            db=db,
            type_evenement="pay_connect_solde",
            description=f"Pay & Connect via solde ({minutes} min, {montant}€)",
            user_id=user.id,
            poste_id=poste_id,
        )
        return session

    # ---------------------------------------------------------
    # Demande anonyme, encaissée en espèces par un opérateur
    # ---------------------------------------------------------
    @staticmethod
    def creer_demande(db: Session, poste_id: int, minutes: int) -> PayConnectRequest:
        PayConnectService._verifier_poste_disponible(db, poste_id)
        montant = PayConnectService._prix_pour(db, minutes)

        demande = PayConnectRequest(poste_id=poste_id, minutes=minutes, montant=montant)
        db.add(demande)
        db.commit()
        db.refresh(demande)

        HistoriqueService.log(
            db=db,
            type_evenement="pay_connect_request",
            description=f"Demande Pay & Connect ({minutes} min, {montant}€) sur poste {poste_id}",
            poste_id=poste_id,
        )

        manager.broadcast_to_admins_threadsafe("pay_connect_pending", {
            "id": demande.id, "poste_id": poste_id, "minutes": minutes, "montant": montant,
        })
        return demande

    @staticmethod
    def annuler_demande(db: Session, request_id: int, poste_id: int) -> None:
        demande = db.query(PayConnectRequest).get(request_id)
        if not demande or demande.poste_id != poste_id or demande.statut != StatutPayConnect.EN_ATTENTE:
            raise ValueError("Demande introuvable ou déjà traitée")

        demande.statut = StatutPayConnect.ANNULE
        demande.date_traitement = datetime.utcnow()
        db.commit()

        manager.broadcast_to_admins_threadsafe("pay_connect_cancelled", {"id": demande.id, "poste_id": poste_id})

    @staticmethod
    def lister_en_attente(db: Session) -> list[PayConnectRequest]:
        return (
            db.query(PayConnectRequest)
            .filter(PayConnectRequest.statut == StatutPayConnect.EN_ATTENTE)
            .order_by(PayConnectRequest.date_creation.asc())
            .all()
        )

    @staticmethod
    def confirmer(db: Session, request_id: int, operateur_id: int) -> PayConnectRequest:
        demande = db.query(PayConnectRequest).get(request_id)
        if not demande:
            raise ValueError("Demande introuvable")
        if demande.statut != StatutPayConnect.EN_ATTENTE:
            raise ValueError("Cette demande a déjà été traitée")

        # Ticket interne, jamais communiqué au client : sert uniquement à satisfaire la
        # contrainte Session(user_id|ticket_id) sans rendre la session transférable ni
        # réutilisable — marqué consommé dès sa création.
        ticket = Ticket(
            code=f"paycon-{uuid.uuid4().hex}",
            description=f"Pay & Connect poste {demande.poste_id}",
            type_ticket=TypeTicket.POSTE,
            restant_minutes=demande.minutes,
            est_actif=True,
            est_consomme=True,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        PaiementService.creer_paiement(
            db=db, montant=demande.montant, type_paiement=TypePaiement.ESPECES,
            ticket_id=ticket.id, operateur_id=operateur_id,
        )

        session = SessionService.demarrer_session(db=db, poste_id=demande.poste_id, ticket_id=ticket.id)

        demande.statut = StatutPayConnect.CONFIRME
        demande.operateur_id = operateur_id
        demande.ticket_id = ticket.id
        demande.session_id = session.id
        demande.date_traitement = datetime.utcnow()
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="pay_connect_confirm",
            description=f"Pay & Connect confirmé ({demande.minutes} min, {demande.montant}€)",
            operateur_id=operateur_id,
            poste_id=demande.poste_id,
        )
        return demande

    @staticmethod
    def refuser(db: Session, request_id: int, operateur_id: int) -> PayConnectRequest:
        demande = db.query(PayConnectRequest).get(request_id)
        if not demande:
            raise ValueError("Demande introuvable")
        if demande.statut != StatutPayConnect.EN_ATTENTE:
            raise ValueError("Cette demande a déjà été traitée")

        demande.statut = StatutPayConnect.REFUSE
        demande.operateur_id = operateur_id
        demande.date_traitement = datetime.utcnow()
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="pay_connect_refuse",
            description="Pay & Connect refusé",
            operateur_id=operateur_id,
            poste_id=demande.poste_id,
        )

        manager.send_to_poste_threadsafe(demande.poste_id, "pay_connect_refused", {"id": demande.id})
        return demande
