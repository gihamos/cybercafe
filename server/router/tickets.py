from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from config.database import get_db
from models.ticket import Ticket
from models.offre import Offre
from utils.code_generator import generate_code

router = APIRouter(prefix="/tickets", tags=["tickets"])

# -----------------------------
# 1. Générer un ticket
# -----------------------------
@router.post("/generate")
def generate_ticket(forfait_id: int, db: Session = Depends(get_db)):
    forfait = db.query(Offre).filter(Forfait.id == forfait_id).first()
    if not forfait:
        raise HTTPException(404, "Forfait introuvable")

    code = generate_code()

    ticket = Ticket(
        code=code,
        forfait_id=forfait_id,
        temps_restant=forfait.duree_minutes
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {"code": code, "forfait": forfait.nom, "temps": ticket.temps_restant}

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
