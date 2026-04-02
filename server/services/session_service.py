from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.session import Session as SessionModel, is_valid_session
from models.poste import Poste
from models.user import User
from models.ticket import Ticket
from models.abonnement import Abonnement
from models.achat import Achat

from server.services.notification_service import NotificationService
from server.services.historique_service import HistoriqueService
from models.notification import TypeNotification


class SessionService:

    # ---------------------------------------------------------
    # 1. DÉMARRER UNE SESSION
    # ---------------------------------------------------------
    @staticmethod
    def demarrer_session(
        db: Session,
        poste_id: int,
        user_id: int | None = None,
        ticket_id: int | None = None,
        abonnement_id: int | None = None,
        achat_id: int | None = None
    ):
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")

        if poste.est_verrouille:
            raise ValueError("Poste déjà occupé")

        # Récupération des limites selon l'offre
        limite_minutes = None
        limite_data_mo = None

        if abonnement_id:
            abo = db.query(Abonnement).get(abonnement_id)
            if not abo:
                raise ValueError("Abonnement introuvable")
            limite_minutes = abo.limite_minutes
            limite_data_mo = abo.limite_data_mo

        if achat_id:
            achat = db.query(Achat).get(achat_id)
            if not achat:
                raise ValueError("Achat introuvable")
            limite_minutes = achat.limite_minutes
            limite_data_mo = achat.limite_data_mo

        session = SessionModel(
            poste_id=poste_id,
            user_id=user_id,
            ticket_id=ticket_id,
            abonnement_id=abonnement_id,
            achat_id=achat_id,
            date_debut=datetime.utcnow(),
            est_active=True,
            est_terminee=False,
            limite_minutes=limite_minutes,
            limite_data_mo=limite_data_mo
        )

        poste.occupe = True

        db.add(session)
        db.commit()
        db.refresh(session)

        HistoriqueService.log(
            db=db,
            type_evenement="session_start",
            description=f"Session démarrée sur poste {poste_id}",
            user_id=user_id,
            ticket_id=ticket_id,
            poste_id=poste_id
        )

        return session

    # ---------------------------------------------------------
    # 2. FERMER UNE SESSION
    # ---------------------------------------------------------
    @staticmethod
    def fermer_session(db: Session, session_id: int):
        session = db.query(SessionModel).get(session_id)
        if not session:
            raise ValueError("Session introuvable")

        if not session.est_active:
            return session

        session.est_active = False
        session.est_terminee = True
        session.date_fin = datetime.utcnow()

        # libérer le poste
        session.poste.est_verrouille=False

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="session_end",
            description=f"Session terminée sur poste {session.poste_id}",
            user_id=session.user_id,
            ticket_id=session.ticket_id,
            poste_id=session.poste_id
        )

        # notification user
        if session.user_id:
            NotificationService.send_to_user(
                db=db,
                user_id=session.user_id,
                titre="Session terminée",
                message="Votre session est maintenant terminée.",
                type_notification=TypeNotification.SESSION
            )

        return session

    # ---------------------------------------------------------
    # 3. CHANGER DE POSTE
    # ---------------------------------------------------------
    @staticmethod
    def changer_poste(db: Session, session_id: int, nouveau_poste_id: int):
        session = db.query(SessionModel).get(session_id)
        if not session:
            raise ValueError("Session introuvable")

        ancien_poste = session.poste
        nouveau_poste = db.query(Poste).get(nouveau_poste_id)

        if not nouveau_poste:
            raise ValueError("Nouveau poste introuvable")

        if nouveau_poste.est_verrouille:
            raise ValueError("Nouveau poste n'est pas disponible")
        
        if not nouveau_poste.est_en_ligne:
            raise ValueError("le poste est hors ligne")

        ancien_poste.occupe = False
        nouveau_poste.occupe = True

        session.poste_id = nouveau_poste_id
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="session_move",
            description=f"Session déplacée du poste {ancien_poste.id} au poste {nouveau_poste_id}",
            user_id=session.user_id,
            poste_id=nouveau_poste_id
        )

        return session

    # ---------------------------------------------------------
    # 4. CONSOMMATION TEMPS
    # ---------------------------------------------------------
    @staticmethod
    def consommer_minutes(db: Session, session_id: int, minutes: int):
        session = db.query(SessionModel).get(session_id)
        if not session:
            raise ValueError("Session introuvable")

        session.consommation_minutes += minutes

        # vérifier limite
        if session.limite_minutes and session.consommation_minutes >= session.limite_minutes:
            SessionService.fermer_session(db, session_id)

        db.commit()
        return session

    # ---------------------------------------------------------
    # 5. CONSOMMATION DATA
    # ---------------------------------------------------------
    @staticmethod
    def consommer_data(db: Session, session_id: int, mo: float):
        session = db.query(SessionModel).get(session_id)
        if not session:
            raise ValueError("Session introuvable")

        session.consommation_data_mo += mo

        # vérifier limite
        if session.limite_data_mo and session.consommation_data_mo >= session.limite_data_mo:
            SessionService.fermer_session(db, session_id)

        db.commit()
        return session

    # ---------------------------------------------------------
    # 6. VÉRIFIER LES SESSIONS EXPIRÉES
    # ---------------------------------------------------------
    @staticmethod
    def verifier_expirations(db: Session):
        sessions = db.query(SessionModel).filter(SessionModel.est_active == True).all()
        now = datetime.utcnow()

        for s in sessions:
            valid = is_valid_session(s)
            if not valid["valide"]:
                SessionService.fermer_session(db, s.id)

    # ---------------------------------------------------------
    # 7. RÉCUPÉRER LES SESSIONS ACTIVES
    # ---------------------------------------------------------
    @staticmethod
    def get_sessions_actives(db: Session):
        return (
            db.query(SessionModel)
            .filter(SessionModel.est_active == True)
            .order_by(SessionModel.date_debut.desc())
            .all()
        )

    # ---------------------------------------------------------
    # 8. RÉCUPÉRER LES SESSIONS D’UN USER
    # ---------------------------------------------------------
    @staticmethod
    def get_sessions_user(db: Session, user_id: int):
        return (
            db.query(SessionModel)
            .filter(SessionModel.user_id == user_id)
            .order_by(SessionModel.date_debut.desc())
            .all()
        )

    # ---------------------------------------------------------
    # 9. RÉCUPÉRER LES SESSIONS D’UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def get_sessions_poste(db: Session, poste_id: int):
        return (
            db.query(SessionModel)
            .filter(SessionModel.poste_id == poste_id)
            .order_by(SessionModel.date_debut.desc())
            .all()
        )

    # ---------------------------------------------------------
    # 10. FORCER LA FERMETURE
    # ---------------------------------------------------------
    @staticmethod
    def forcer_fermeture(db: Session, session_id: int):
        return SessionService.fermer_session(db, session_id)
