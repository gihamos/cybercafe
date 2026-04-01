from fastapi import APIRouter, Depends, HTTPException
from config.database import get_db
from schemas.session import Session_start
from sqlalchemy.orm import Session
from models.sessions import Session as SessionModel
from models.user import User,is_validUser
from models.abonnement import is_valide_abonnement
from models.ticket import Ticket
from datetime import date



router = APIRouter(prefix="/session", tags=["sessions"])

@router.post("/start")
def start_session(session_input:Session_start,db:Session=Depends(get_db)):
    if(session_input.username is None and session_input.code is None) or(session_input.username is not None and session_input.code is not None):
        raise HTTPException(status_code=400,detail=" un seul des paramètres doit etre saisi : <<username>> ou code pour le ticket")
    session=SessionModel()
    if session_input.username is not None:
        user=db.query(User).filter(User.username==session_input.username).first()
        if user is None:
            raise HTTPException(status_code=400,detail=f"impossible de demarrer la session, le username : {session_input.username} n'est associé à aucun compte")
        validuser=is_validUser(user=user)
        if not validuser["valide"]: 
             raise HTTPException(status_code=400,detail=validuser["detail"])
        validabon = is_valide_abonnement(user.current_abonnement) if user.current_abonnement else None
        if not validabon or not validabon["valide"]:
            raise HTTPException(status_code=400,detail=validabon["detail"]or "Abonnemnt inexistant")
        
        session.user_id=user.id
    
    if session_input.code is not None:
        ticket=db.query(Ticket).filter(Ticket.code==session_input.code).first()
        if ticket is None:
            raise HTTPException(status_code=400,detail=f"impossible de demarrer la session, le ticket : {session_input.code} n'existe pas")
        if ticket.date_expiration is not None and ticket.date_expiration<date.today() : 
            raise HTTPException(status_code=400,detail=f" impossible de demarrer la session, le ticket : {session_input.username} est expiré")
        if ticket.restant_minutes is not None and ticket.restant_minutes<=5 : 
            raise HTTPException(status_code=400,detail=f" impossible de demarrer la session,  le ticket : {session_input.username} n'a plus de temps")
        if ticket.restant_data is not None and ticket.restant_data<=10 : 
            raise HTTPException(status_code=400,detail=f" impossible de demarrer la session,  le ticket : {session_input.username} n'a plus de data")
        session.ticket_id=ticket.id
        if  ticket.restant_data is not None:
            session.
            
    