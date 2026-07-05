from sqlalchemy.orm import Session

from models.offre import Offre, OffreTemps, OffreData, OffreIllimite, TypeOffre
from services.historique_service import HistoriqueService


class OffreService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE OFFRE (polymorphe selon le type)
    # ---------------------------------------------------------
    @staticmethod
    def creer_offre(db: Session, data: dict):
        data = dict(data)
        type_offre = data.pop("type_offre")
        duree_minutes = data.pop("duree_minutes", None)
        quota_mo = data.pop("quota_mo", None)

        if db.query(Offre).filter(Offre.nom == data.get("nom")).first():
            raise ValueError("Une offre avec ce nom existe déjà")

        if type_offre == TypeOffre.TEMPS:
            if duree_minutes is None:
                raise ValueError("duree_minutes est requis pour une offre de type temps")
            offre = OffreTemps(**data, type_offre=type_offre, duree_minutes=duree_minutes)
        elif type_offre == TypeOffre.DATA:
            if quota_mo is None:
                raise ValueError("quota_mo est requis pour une offre de type data")
            offre = OffreData(**data, type_offre=type_offre, quota_mo=quota_mo)
        elif type_offre == TypeOffre.ILLIMITE:
            offre = OffreIllimite(**data, type_offre=type_offre)
        else:
            raise ValueError("Type d'offre invalide")

        db.add(offre)
        db.commit()
        db.refresh(offre)

        HistoriqueService.log(
            db=db,
            type_evenement="offre_create",
            description=f"Création de l'offre {offre.nom}",
            details={"type_offre": type_offre, "prix": offre.prix}
        )

        return offre

    # ---------------------------------------------------------
    # 2. METTRE À JOUR UNE OFFRE
    # ---------------------------------------------------------
    @staticmethod
    def update_offre(db: Session, offre_id: int, data: dict):
        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")

        for key, value in data.items():
            if hasattr(offre, key) and value is not None:
                setattr(offre, key, value)

        db.commit()
        db.refresh(offre)

        HistoriqueService.log(
            db=db,
            type_evenement="offre_update",
            description=f"Modification de l'offre {offre.nom}",
            details=data
        )

        return offre

    # ---------------------------------------------------------
    # 3. ACTIVER / DÉSACTIVER
    # ---------------------------------------------------------
    @staticmethod
    def set_actif(db: Session, offre_id: int, actif: bool):
        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")

        offre.is_actif = actif
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="offre_status",
            description=f"Offre {offre.nom} {'activée' if actif else 'désactivée'}"
        )

        return offre

    # ---------------------------------------------------------
    # 4. SUPPRIMER
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_offre(db: Session, offre_id: int):
        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")

        db.delete(offre)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="offre_delete",
            description=f"Suppression de l'offre {offre.nom}"
        )

        return True

    # ---------------------------------------------------------
    # 5. RECHERCHE
    # ---------------------------------------------------------
    @staticmethod
    def rechercher_offres(
        db: Session,
        type_offre: TypeOffre | None = None,
        is_actif: bool | None = None,
        nom: str | None = None
    ):
        query = db.query(Offre)

        if type_offre is not None:
            query = query.filter(Offre.type_offre == type_offre)

        if is_actif is not None:
            query = query.filter(Offre.is_actif == is_actif)

        if nom:
            query = query.filter(Offre.nom.ilike(f"%{nom}%"))

        return query.order_by(Offre.nom.asc()).all()

    @staticmethod
    def get_by_id(db: Session, offre_id: int):
        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")
        return offre
