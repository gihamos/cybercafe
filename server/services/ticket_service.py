from datetime import date

from sqlalchemy.orm import Session

from models.ticket import Ticket, TypeTicket
from services.historique_service import HistoriqueService


class TicketService:

    @staticmethod
    def lister(
        db: Session,
        actif: bool | None = None,
        consomme: bool | None = None,
        offre_id: int | None = None,
    ) -> list[Ticket]:
        query = db.query(Ticket)
        if actif is not None:
            query = query.filter(Ticket.est_actif == actif)
        if consomme is not None:
            query = query.filter(Ticket.est_consomme == consomme)
        if offre_id is not None:
            query = query.filter(Ticket.offre_id == offre_id)
        return query.order_by(Ticket.date_achat.desc()).all()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Ticket:
        ticket = db.query(Ticket).filter(Ticket.code == code).first()
        if not ticket:
            raise ValueError("Ticket introuvable")
        return ticket

    @staticmethod
    def modifier(db: Session, code: str, data: dict) -> Ticket:
        ticket = TicketService.get_by_code(db, code)
        for key, value in data.items():
            if hasattr(ticket, key) and value is not None:
                setattr(ticket, key, value)

        db.commit()
        db.refresh(ticket)

        HistoriqueService.log(
            db=db, type_evenement="ticket_update",
            description=f"Modification du ticket '{code}'", details=data
        )
        return ticket

    @staticmethod
    def set_actif(db: Session, code: str, actif: bool) -> Ticket:
        ticket = TicketService.get_by_code(db, code)
        ticket.est_actif = actif
        db.commit()
        db.refresh(ticket)

        HistoriqueService.log(
            db=db, type_evenement="ticket_update",
            description=f"Ticket '{code}' {'activé' if actif else 'désactivé'}"
        )
        return ticket

    @staticmethod
    def renforcer(db: Session, code: str, minutes_ajoutees: int = 0, data_ajoutee_mo: float = 0) -> Ticket:
        """Ajoute du temps/de la data à un ticket déjà émis (ex: geste commercial)."""
        ticket = TicketService.get_by_code(db, code)
        if minutes_ajoutees:
            ticket.restant_minutes = (ticket.restant_minutes or 0) + minutes_ajoutees
        if data_ajoutee_mo:
            ticket.restant_data_mo = (ticket.restant_data_mo or 0) + data_ajoutee_mo

        db.commit()
        db.refresh(ticket)

        HistoriqueService.log(
            db=db, type_evenement="ticket_update",
            description=f"Ticket '{code}' renforcé (+{minutes_ajoutees} min, +{data_ajoutee_mo} Mo)"
        )
        return ticket

    # ---------------------------------------------------------
    # BONS DE RECHARGE (tickets crédit)
    # ---------------------------------------------------------
    @staticmethod
    def utiliser_credit(db: Session, code: str, user_iden: int | str, operateur_id: int | None = None):
        """Échange un bon de recharge contre du crédit sur le solde d'un compte.
        Le bon est consommé en une fois (pas d'utilisation partielle)."""
        from models.paiement import TypePaiement
        from services.user_service import UserService

        ticket = db.query(Ticket).filter(Ticket.code == code.strip().upper()).first()
        if not ticket:
            raise ValueError("Code inconnu")
        if ticket.type_ticket != TypeTicket.CREDIT or not ticket.credit_euros:
            raise ValueError("Ce code n'est pas un bon de recharge")
        if not ticket.est_actif:
            raise ValueError("Ce bon est désactivé")
        if ticket.est_consomme:
            raise ValueError("Ce bon a déjà été utilisé")
        if ticket.date_expiration and ticket.date_expiration.date() < date.today():
            raise ValueError("Ce bon est expiré")

        nouveau_solde = UserService.ajouter_solde(
            db=db, user_iden=user_iden, montant=ticket.credit_euros,
            type_paiement=TypePaiement.CODE_PREPAYE, operateur_id=operateur_id,
        )
        ticket.est_consomme = True
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement",
            description=f"Bon de recharge {ticket.code} utilisé ({ticket.credit_euros}€)",
            ticket_id=ticket.id,
            operateur_id=operateur_id,
            details={"credit_euros": ticket.credit_euros},
        )
        return ticket, nouveau_solde
