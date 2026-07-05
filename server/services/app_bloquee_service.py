from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.app_bloquee import AppBloquee, PlateformeApp
from services.historique_service import HistoriqueService
from websocket.manager import manager


class AppBloqueeService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE RÈGLE DE BLOCAGE
    # ---------------------------------------------------------
    @staticmethod
    def creer_regle(
        db: Session,
        nom_processus: str,
        plateforme: PlateformeApp = PlateformeApp.TOUS,
        poste_id: int | None = None,
        description: str | None = None
    ):
        regle = AppBloquee(
            nom_processus=nom_processus,
            plateforme=plateforme,
            poste_id=poste_id,
            description=description,
            actif=True
        )
        db.add(regle)
        db.commit()
        db.refresh(regle)

        HistoriqueService.log(
            db=db,
            type_evenement="app_bloquee_create",
            description=f"Ajout de la règle de blocage : {nom_processus}",
            poste_id=poste_id,
            details={"plateforme": plateforme}
        )

        AppBloqueeService._diffuser(db, poste_id)
        return regle

    # ---------------------------------------------------------
    # 2. METTRE À JOUR UNE RÈGLE
    # ---------------------------------------------------------
    @staticmethod
    def update_regle(db: Session, regle_id: int, data: dict):
        regle = db.query(AppBloquee).get(regle_id)
        if not regle:
            raise ValueError("Règle introuvable")

        for key, value in data.items():
            if hasattr(regle, key) and value is not None:
                setattr(regle, key, value)

        db.commit()
        db.refresh(regle)

        HistoriqueService.log(
            db=db,
            type_evenement="app_bloquee_update",
            description=f"Modification de la règle {regle.nom_processus}",
            poste_id=regle.poste_id,
            details=data
        )

        AppBloqueeService._diffuser(db, regle.poste_id)
        return regle

    # ---------------------------------------------------------
    # 3. SUPPRIMER UNE RÈGLE
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_regle(db: Session, regle_id: int):
        regle = db.query(AppBloquee).get(regle_id)
        if not regle:
            raise ValueError("Règle introuvable")

        poste_id = regle.poste_id
        nom = regle.nom_processus

        db.delete(regle)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="app_bloquee_delete",
            description=f"Suppression de la règle {nom}",
            poste_id=poste_id
        )

        AppBloqueeService._diffuser(db, poste_id)
        return True

    # ---------------------------------------------------------
    # 4. LISTER (admin)
    # ---------------------------------------------------------
    @staticmethod
    def lister(db: Session, poste_id: int | None = None):
        query = db.query(AppBloquee)
        if poste_id is not None:
            query = query.filter(or_(AppBloquee.poste_id == poste_id, AppBloquee.poste_id.is_(None)))
        return query.order_by(AppBloquee.nom_processus.asc()).all()

    # ---------------------------------------------------------
    # 5. RÉSOUDRE LES RÈGLES APPLICABLES À UN POSTE (globales + spécifiques)
    # ---------------------------------------------------------
    @staticmethod
    def get_regles_pour_poste(db: Session, poste_id: int) -> list[str]:
        regles = (
            db.query(AppBloquee)
            .filter(AppBloquee.actif == True)
            .filter(or_(AppBloquee.poste_id == poste_id, AppBloquee.poste_id.is_(None)))
            .all()
        )
        return [r.nom_processus for r in regles]

    # ---------------------------------------------------------
    # 6. DIFFUSER LA LISTE À JOUR AUX POSTES CONCERNÉS
    # ---------------------------------------------------------
    @staticmethod
    def _diffuser(db: Session, poste_id: int | None):
        if poste_id is not None:
            apps = AppBloqueeService.get_regles_pour_poste(db, poste_id)
            manager.send_to_poste_threadsafe(poste_id, "blocked_apps", {"apps": apps})
        else:
            # règle globale : rediffuser à tous les postes actuellement connectés
            for pid in list(manager.active_connections.keys()):
                apps = AppBloqueeService.get_regles_pour_poste(db, pid)
                manager.send_to_poste_threadsafe(pid, "blocked_apps", {"apps": apps})
