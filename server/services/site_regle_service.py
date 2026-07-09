from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.site_regle import SiteRegle
from models.session import Session as SessionModel
from models.user import User
from services.historique_service import HistoriqueService
from websocket.manager import manager


class SiteRegleService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE RÈGLE
    # ---------------------------------------------------------
    @staticmethod
    def creer_regle(db: Session, domaine: str, groupe_id: int | None = None, description: str | None = None):
        regle = SiteRegle(domaine=domaine.lower().strip(), groupe_id=groupe_id, description=description, actif=True)
        db.add(regle)
        db.commit()
        db.refresh(regle)

        HistoriqueService.log(
            db=db, type_evenement="site_regle_create",
            description=f"Blocage du site '{regle.domaine}'",
            details={"groupe_id": groupe_id}
        )

        SiteRegleService._diffuser(db, groupe_id)
        return regle

    # ---------------------------------------------------------
    # 2. METTRE À JOUR
    # ---------------------------------------------------------
    @staticmethod
    def update_regle(db: Session, regle_id: int, data: dict):
        regle = db.query(SiteRegle).get(regle_id)
        if not regle:
            raise ValueError("Règle introuvable")

        for key, value in data.items():
            if hasattr(regle, key) and value is not None:
                setattr(regle, key, value)

        db.commit()
        db.refresh(regle)

        HistoriqueService.log(db=db, type_evenement="site_regle_update", description=f"Modification de la règle '{regle.domaine}'")
        SiteRegleService._diffuser(db, regle.groupe_id)
        return regle

    # ---------------------------------------------------------
    # 3. SUPPRIMER
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_regle(db: Session, regle_id: int):
        regle = db.query(SiteRegle).get(regle_id)
        if not regle:
            raise ValueError("Règle introuvable")

        groupe_id, domaine = regle.groupe_id, regle.domaine
        db.delete(regle)
        db.commit()

        HistoriqueService.log(db=db, type_evenement="site_regle_delete", description=f"Suppression de la règle '{domaine}'")
        SiteRegleService._diffuser(db, groupe_id)
        return True

    # ---------------------------------------------------------
    # 4. LISTER (admin)
    # ---------------------------------------------------------
    @staticmethod
    def lister(db: Session, groupe_id: int | None = None):
        query = db.query(SiteRegle)
        if groupe_id is not None:
            query = query.filter(or_(SiteRegle.groupe_id == groupe_id, SiteRegle.groupe_id.is_(None)))
        return query.order_by(SiteRegle.domaine.asc()).all()

    # ---------------------------------------------------------
    # 5. RÉSOUDRE LES DOMAINES BLOQUÉS POUR LA SESSION D'UN POSTE
    # ---------------------------------------------------------
    @staticmethod
    def get_domaines_pour_session(db: Session, poste_id: int) -> list[str]:
        session = (
            db.query(SessionModel)
            .filter(SessionModel.poste_id == poste_id, SessionModel.est_active == True)
            .first()
        )

        groupe_id = None
        if session and session.user_id:
            user = db.query(User).get(session.user_id)
            groupe_id = user.groupe_id if user else None

        regles = (
            db.query(SiteRegle)
            .filter(SiteRegle.actif == True)
            .filter(or_(SiteRegle.groupe_id == groupe_id, SiteRegle.groupe_id.is_(None)))
            .all()
        )
        return sorted({r.domaine for r in regles})

    # ---------------------------------------------------------
    # 6. DIFFUSER AUX POSTES CONCERNÉS
    # ---------------------------------------------------------
    @staticmethod
    def _diffuser(db: Session, groupe_id: int | None):
        for pid in list(manager.active_connections.keys()):
            domaines = SiteRegleService.get_domaines_pour_session(db, pid)
            manager.send_to_poste_threadsafe(pid, "blocked_sites", {"domaines": domaines})
