from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from config.database import get_db
from models.ticket import Ticket
from models.offre import Offre
from utils.code_generator import generate_code

from dependencies.access import require_roles
from dependencies.auth import auth_dependency
from models.user import UserRole


router = APIRouter(prefix="/tickets", tags=["tickets"])


# -----------------------------
# 1. Générer un ticket
# -----------------------------
@router.post("/generate", status_code=201,dependencies=[Depends(auth_dependency),Depends(require_roles(allowed_roles=[UserRole.admin]))])
def generate_ticket(forfait_id: int, nbticket: int = 1, db: Session = Depends(get_db)):
    forfait = db.query(Offre).filter(Offre.id == forfait_id).first()
    
    if not forfait:
        raise HTTPException(status_code=404, detail="Forfait introuvable")

    tab = []

    for _ in range(1,nbticket):
        # génération code unique
        while True:
            code = generate_code()
            exists = db.query(Ticket).filter(Ticket.code == code).first()
            if not exists:
                break

        ticket = Ticket(
            code=code,
            forfait_id=forfait_id,
            temps_restant=forfait.duree_minutes
        )

        db.add(ticket)
        tab.append(ticket)

    try:
        db.commit()
    except:
        db.rollback()
        raise


    for ticket in tab:
        db.refresh(ticket)

    return {
        "status_code": 201,
        "data": [
            {
                "code": ticket.code,
                "forfait": forfait.nom,
                "temps": ticket.temps_restant
            }
            for ticket in tab
        ]
    }



# -----------------------------
# 2. Vérifier un ticket
# -----------------------------
@router.get("/check/{code}")
def check_ticket(code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.code == code).first()

    if not ticket:
        raise HTTPException(404, "Ticket invalide")

    if ticket.utilise:
        raise HTTPException(400, "Ticket déjà utilisé")

    return {
        "valid": True,
        "forfait": ticket.forfait.nom,
        "temps_restant": ticket.temps_restant
    }

# -----------------------------
# 3. Marquer un ticket comme utilisé
# -----------------------------
@router.post("/use/{code}")
def use_ticket(code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.code == code).first()

    if not ticket:
        raise HTTPException(404, "Ticket invalide")

    if ticket.utilise:
        raise HTTPException(400, "Ticket déjà utilisé")

    ticket.utilise = True
    ticket.date_utilisation = datetime.utcnow()

    db.commit()

    return {"message": "Ticket validé", "temps_restant": ticket.temps_restant}
