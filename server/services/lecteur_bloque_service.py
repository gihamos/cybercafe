from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.lecteur_bloque import LecteurBloque, PlateformeLecteur, TypeLecteur
from services.historique_service import HistoriqueService
from websocket.manager import manager


class LecteurBloqueService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE RÈGLE DE BLOCAGE
    # ---------------------------------------------------------
    @staticmethod
    def creer_regle(
        db: Session,
        type_lecteur: TypeLecteur,
        plateforme: PlateformeLecteur = PlateformeLecteur.TOUS,
        poste_id: int | None = None,
        description: str | None = None
    ):
        regle = LecteurBloque(
            type_lecteur=type_lecteur,
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
            type_evenement="lecteur_bloque_create",
            description=f"Ajout de la règle de blocage de lecteur : {type_lecteur.value}",
            poste_id=poste_id,
            details={"plateforme": plateforme}
        )

        LecteurBloqueService._diffuser(db, poste_id)
        return regle

    # ---------------------------------------------------------
    # 2. METTRE À JOUR UNE RÈGLE
    # ---------------------------------------------------------
    @staticmethod
    def update_regle(db: Session, regle_id: int, data: dict):
        regle = db.query(LecteurBloque).get(regle_id)
        if not regle:
            raise ValueError("Règle introuvable")

        for key, value in data.items():
            if hasattr(regle, key) and value is not None:
                setattr(regle, key, value)

        db.commit()
        db.refresh(regle)

        HistoriqueService.log(
            db=db,
            type_evenement="lecteur_bloque_update",
            description=f"Modification de la règle {regle.type_lecteur.value}",
            poste_id=regle.poste_id,
            details=data
        )

        LecteurBloqueService._diffuser(db, regle.poste_id)
        return regle

    # ---------------------------------------------------------
    # 3. SUPPRIMER UNE RÈGLE
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_regle(db: Session, regle_id: int):
        regle = db.query(LecteurBloque).get(regle_id)
        if not regle:
            raise ValueError("Règle introuvable")

        poste_id = regle.poste_id
        type_lecteur = regle.type_lecteur

        db.delete(regle)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="lecteur_bloque_delete",
            description=f"Suppression de la règle {type_lecteur.value}",
            poste_id=poste_id
        )

        LecteurBloqueService._diffuser(db, poste_id)
        return True

    # ---------------------------------------------------------
    # 4. LISTER (admin)
    # ---------------------------------------------------------
    @staticmethod
    def lister(db: Session, poste_id: int | None = None):
        query = db.query(LecteurBloque)
        if poste_id is not None:
            query = query.filter(or_(LecteurBloque.poste_id == poste_id, LecteurBloque.poste_id.is_(None)))
        return query.order_by(LecteurBloque.type_lecteur.asc()).all()

    # ---------------------------------------------------------
    # 5. RÉSOUDRE LES RÈGLES APPLICABLES À UN POSTE (globales + spécifiques)
    # ---------------------------------------------------------
    @staticmethod
    def get_regles_pour_poste(db: Session, poste_id: int) -> list[str]:
        regles = (
            db.query(LecteurBloque)
            .filter(LecteurBloque.actif == True)
            .filter(or_(LecteurBloque.poste_id == poste_id, LecteurBloque.poste_id.is_(None)))
            .all()
        )
        return sorted({r.type_lecteur for r in regles})

    # ---------------------------------------------------------
    # 6. DIFFUSER LA LISTE À JOUR AUX POSTES CONCERNÉS
    # ---------------------------------------------------------
    @staticmethod
    def _diffuser(db: Session, poste_id: int | None):
        if poste_id is not None:
            types = LecteurBloqueService.get_regles_pour_poste(db, poste_id)
            manager.send_to_poste_threadsafe(poste_id, "blocked_drives", {"types": types})
        else:
            # règle globale : rediffuser à tous les postes actuellement connectés
            for pid in list(manager.active_connections.keys()):
                types = LecteurBloqueService.get_regles_pour_poste(db, pid)
                manager.send_to_poste_threadsafe(pid, "blocked_drives", {"types": types})
