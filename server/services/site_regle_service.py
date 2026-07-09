from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.site_regle import SiteRegle
from models.session import Session as SessionModel
from models.user import User, get_age
from services.historique_service import HistoriqueService
from websocket.manager import manager


class SiteRegleService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE RÈGLE
    # ---------------------------------------------------------
    @staticmethod
    def creer_regle(
        db: Session, domaine: str, groupe_id: int | None = None,
        description: str | None = None, age_min: int | None = None
    ):
        regle = SiteRegle(
            domaine=domaine.lower().strip(), groupe_id=groupe_id,
            description=description, age_min=age_min, actif=True
        )
        db.add(regle)
        db.commit()
        db.refresh(regle)

        HistoriqueService.log(
            db=db, type_evenement="site_regle_create",
            description=f"Blocage du site '{regle.domaine}'",
            details={"groupe_id": groupe_id, "age_min": age_min}
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

        groupe_ids: list[int] = []
        age = None
        if session and session.user_id:
            user = db.query(User).get(session.user_id)
            if user:
                groupe_ids = [g.id for g in user.groupes]
                age = get_age(user)

        query = db.query(SiteRegle).filter(SiteRegle.actif == True)
        if groupe_ids:
            query = query.filter(or_(SiteRegle.groupe_id.in_(groupe_ids), SiteRegle.groupe_id.is_(None)))
        else:
            query = query.filter(SiteRegle.groupe_id.is_(None))

        domaines = set()
        for r in query.all():
            if r.age_min is None:
                domaines.add(r.domaine)
            elif age is None or age < r.age_min:
                # âge inconnu (ticket anonyme) ou client trop jeune : bloqué par défaut
                domaines.add(r.domaine)

        return sorted(domaines)

    # ---------------------------------------------------------
    # 6. DIFFUSER AUX POSTES CONCERNÉS
    # ---------------------------------------------------------
    @staticmethod
    def _diffuser(db: Session, groupe_id: int | None):
        for pid in list(manager.active_connections.keys()):
            domaines = SiteRegleService.get_domaines_pour_session(db, pid)
            manager.send_to_poste_threadsafe(pid, "blocked_sites", {"domaines": domaines})
