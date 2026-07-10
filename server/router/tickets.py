from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.database import get_db
from models.ticket import Ticket, TypeTicket
from models.offre import Offre, TypeOffre
from utils.code_generator import generate_code
from schemas.ticket_schema import TicketUpdate
from services.ticket_service import TicketService

from dependencies.access import require_roles, require_permission
from dependencies.auth import auth_dependency
from models.user import UserRole


router = APIRouter(prefix="/tickets", tags=["tickets"])


def _serialize(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "code": ticket.code,
        "description": ticket.description,
        "type_ticket": ticket.type_ticket,
        "offre_id": ticket.offre_id,
        "offre_nom": ticket.offre.nom if ticket.offre else None,
        "date_achat": ticket.date_achat,
        "date_expiration": ticket.date_expiration,
        "est_actif": ticket.est_actif,
        "est_consomme": ticket.est_consomme,
        "restant_minutes": ticket.restant_minutes,
        "restant_data_mo": ticket.restant_data_mo,
    }

_TYPE_OFFRE_TO_TICKET = {
    TypeOffre.TEMPS: TypeTicket.TEMPS,
    TypeOffre.DATA: TypeTicket.DATA,
    TypeOffre.ILLIMITE: TypeTicket.ILLIMITE,
}


# -----------------------------
# 1. Générer un ticket
# -----------------------------
@router.post("/generate", status_code=201,dependencies=[Depends(auth_dependency),Depends(require_roles(allowed_roles=[UserRole.admin]))])
def generate_ticket(forfait_id: int, nbticket: int = 1, db: Session = Depends(get_db)):
    forfait = db.query(Offre).filter(Offre.id == forfait_id).first()

    if not forfait:
        raise HTTPException(status_code=404, detail="Forfait introuvable")

    if nbticket < 1:
        raise HTTPException(status_code=400, detail="nbticket doit être supérieur ou égal à 1")

    type_ticket = _TYPE_OFFRE_TO_TICKET.get(forfait.type_offre, TypeTicket.TEMPS)

    tab = []

    for _ in range(nbticket):
        # génération code unique
        while True:
            code = generate_code()
            exists = db.query(Ticket).filter(Ticket.code == code).first()
            if not exists:
                break

        ticket = Ticket(
            code=code,
            type_ticket=type_ticket,
            offre_id=forfait_id,
            date_expiration=forfait.date_expiration,
            restant_minutes=getattr(forfait, "duree_minutes", None),
            restant_data_mo=getattr(forfait, "quota_mo", None)
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
                "temps_restant": ticket.restant_minutes,
                "data_restante": ticket.restant_data_mo
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

    if ticket.est_consomme:
        raise HTTPException(400, "Ticket déjà utilisé")

    return {
        "valid": True,
        "forfait": ticket.offre.nom if ticket.offre else None,
        "temps_restant": ticket.restant_minutes,
        "data_restante": ticket.restant_data_mo
    }

# -----------------------------
# 3. Marquer un ticket comme utilisé
# -----------------------------
@router.post("/use/{code}")
def use_ticket(code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.code == code).first()

    if not ticket:
        raise HTTPException(404, "Ticket invalide")

    if ticket.est_consomme:
        raise HTTPException(400, "Ticket déjà utilisé")

    ticket.est_consomme = True

    db.commit()

    return {"message": "Ticket validé", "temps_restant": ticket.restant_minutes}


# -----------------------------
# 4. LISTER TOUS LES TICKETS (suivi : utilisation, activation, modification)
# -----------------------------
@router.get("/", dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("catalogue"))])
def lister_tickets(
    actif: bool | None = None,
    consomme: bool | None = None,
    offre_id: int | None = None,
    db: Session = Depends(get_db)
):
    tickets = TicketService.lister(db=db, actif=actif, consomme=consomme, offre_id=offre_id)
    return {"status_code": 200, "data": [_serialize(t) for t in tickets]}


@router.patch("/{code}", dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("catalogue"))])
def modifier_ticket(code: str, data: TicketUpdate, db: Session = Depends(get_db)):
    try:
        ticket = TicketService.modifier(db=db, code=code, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(ticket)}


@router.patch("/{code}/desactiver", dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("catalogue"))])
def desactiver_ticket(code: str, db: Session = Depends(get_db)):
    try:
        ticket = TicketService.set_actif(db=db, code=code, actif=False)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(ticket)}


@router.patch("/{code}/reactiver", dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("catalogue"))])
def reactiver_ticket(code: str, db: Session = Depends(get_db)):
    try:
        ticket = TicketService.set_actif(db=db, code=code, actif=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(ticket)}


@router.post("/{code}/renforcer", dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("catalogue"))])
def renforcer_ticket(code: str, minutes: int = 0, data_mo: float = 0, db: Session = Depends(get_db)):
    try:
        ticket = TicketService.renforcer(db=db, code=code, minutes_ajoutees=minutes, data_ajoutee_mo=data_mo)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status_code": 200, "data": _serialize(ticket)}
