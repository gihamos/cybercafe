from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from config.database import get_db
from schemas.session import Session_start
from models.session import Session as SessionModel
from models.user import User, UserRole, is_validUser
from models.abonnement import is_valide_abonnement
from models.ticket import Ticket
from services.session_service import SessionService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(prefix="/session", tags=["sessions"], dependencies=[Depends(auth_dependency)])


def _serialize(session: SessionModel) -> dict:
    return {
        "id": session.id,
        "poste_id": session.poste_id,
        "user_id": session.user_id,
        "ticket_id": session.ticket_id,
        "abonnement_id": session.abonnement_id,
        "date_debut": session.date_debut,
        "date_fin": session.date_fin,
        "est_active": session.est_active,
        "est_terminee": session.est_terminee,
        "consommation_minutes": session.consommation_minutes,
        "consommation_data_mo": session.consommation_data_mo,
        "limite_minutes": session.limite_minutes,
        "limite_data_mo": session.limite_data_mo,
    }


@router.post("/start", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def start_session(session_input: Session_start, db: Session = Depends(get_db)):
    if (session_input.username is None) == (session_input.code is None):
        raise HTTPException(status_code=400, detail="un seul des paramètres doit être saisi : <<username>> ou <<code>> pour le ticket")

    user_id = None
    ticket_id = None
    abonnement_id = None

    if session_input.username is not None:
        user = db.query(User).filter(User.username == session_input.username).first()
        if user is None:
            raise HTTPException(status_code=400, detail=f"le username : {session_input.username} n'est associé à aucun compte")

        validuser = is_validUser(user=user)
        if not validuser["valide"]:
            raise HTTPException(status_code=400, detail=validuser["detail"])

        if not user.current_abonnement:
            raise HTTPException(status_code=400, detail="Aucun abonnement actif n'est associé à ce compte")

        validabon = is_valide_abonnement(user.current_abonnement)
        if not validabon["valide"]:
            raise HTTPException(status_code=400, detail=validabon["detail"])

        user_id = user.id
        abonnement_id = user.current_abonnement_id

    if session_input.code is not None:
        ticket = db.query(Ticket).filter(Ticket.code == session_input.code).first()
        if ticket is None:
            raise HTTPException(status_code=400, detail=f"le ticket : {session_input.code} n'existe pas")

        if not ticket.est_actif or ticket.est_consomme:
            raise HTTPException(status_code=400, detail=f"le ticket : {session_input.code} n'est plus utilisable")

        if ticket.date_expiration is not None and ticket.date_expiration.date() < date.today():
            raise HTTPException(status_code=400, detail=f"le ticket : {session_input.code} est expiré")

        if ticket.restant_minutes is not None and ticket.restant_minutes <= 5:
            raise HTTPException(status_code=400, detail=f"le ticket : {session_input.code} n'a plus assez de temps")

        if ticket.restant_data_mo is not None and ticket.restant_data_mo <= 10:
            raise HTTPException(status_code=400, detail=f"le ticket : {session_input.code} n'a plus assez de data")

        ticket_id = ticket.id

    try:
        session = SessionService.demarrer_session(
            db=db,
            poste_id=session_input.poste_id,
            user_id=user_id,
            ticket_id=ticket_id,
            abonnement_id=abonnement_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status_code": 201,
        "data": _serialize(session)
    }


@router.post("/stop/{session_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def stop_session(session_id: int, db: Session = Depends(get_db)):
    try:
        session = SessionService.fermer_session(db=db, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status_code": 200,
        "data": _serialize(session)
    }


@router.patch("/{session_id}/changer-poste/{nouveau_poste_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def changer_poste(session_id: int, nouveau_poste_id: int, db: Session = Depends(get_db)):
    try:
        session = SessionService.changer_poste(db=db, session_id=session_id, nouveau_poste_id=nouveau_poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status_code": 200,
        "data": _serialize(session)
    }


@router.get("/actives", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_sessions_actives(db: Session = Depends(get_db)):
    sessions = SessionService.get_sessions_actives(db)
    return {
        "status_code": 200,
        "data": [_serialize(s) for s in sessions]
    }


@router.get("/user/{user_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_sessions_user(user_id: int, db: Session = Depends(get_db)):
    sessions = SessionService.get_sessions_user(db, user_id)
    return {
        "status_code": 200,
        "data": [_serialize(s) for s in sessions]
    }


@router.get("/poste/{poste_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_sessions_poste(poste_id: int, db: Session = Depends(get_db)):
    sessions = SessionService.get_sessions_poste(db, poste_id)
    return {
        "status_code": 200,
        "data": [_serialize(s) for s in sessions]
    }
