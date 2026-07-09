from sqlalchemy.orm import Session

from models.user_group import UserGroup
from models.user import User
from services.historique_service import HistoriqueService


class UserGroupService:

    @staticmethod
    def creer(
        db: Session, nom: str, description: str | None = None,
        mode_filtrage: str | None = None, quota_stockage_mo: float | None = None
    ) -> UserGroup:
        if db.query(UserGroup).filter(UserGroup.nom == nom).first():
            raise ValueError(f"Le groupe '{nom}' existe déjà")

        groupe = UserGroup(
            nom=nom, description=description,
            mode_filtrage=mode_filtrage or "liste_noire", quota_stockage_mo=quota_stockage_mo
        )
        db.add(groupe)
        db.commit()
        db.refresh(groupe)

        HistoriqueService.log(db=db, type_evenement="user_group_create", description=f"Création du groupe '{nom}'")
        return groupe

    # ---------------------------------------------------------
    # GESTION DES MEMBRES (un client peut appartenir à plusieurs groupes)
    # ---------------------------------------------------------
    @staticmethod
    def ajouter_membre(db: Session, groupe_id: int, user_id: int) -> UserGroup:
        groupe = db.query(UserGroup).get(groupe_id)
        if not groupe:
            raise ValueError("Groupe introuvable")
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if user not in groupe.membres:
            groupe.membres.append(user)
            db.commit()
            HistoriqueService.log(
                db=db, type_evenement="user_group_update",
                description=f"'{user.username}' ajouté au groupe '{groupe.nom}'", user_id=user_id
            )
        return groupe

    @staticmethod
    def retirer_membre(db: Session, groupe_id: int, user_id: int) -> UserGroup:
        groupe = db.query(UserGroup).get(groupe_id)
        if not groupe:
            raise ValueError("Groupe introuvable")
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if user in groupe.membres:
            groupe.membres.remove(user)
            db.commit()
            HistoriqueService.log(
                db=db, type_evenement="user_group_update",
                description=f"'{user.username}' retiré du groupe '{groupe.nom}'", user_id=user_id
            )
        return groupe

    @staticmethod
    def lister(db: Session) -> list[UserGroup]:
        return db.query(UserGroup).order_by(UserGroup.nom.asc()).all()

    @staticmethod
    def update(db: Session, groupe_id: int, data: dict) -> UserGroup:
        groupe = db.query(UserGroup).get(groupe_id)
        if not groupe:
            raise ValueError("Groupe introuvable")

        for field, value in data.items():
            if value is not None:
                setattr(groupe, field, value)

        db.commit()
        HistoriqueService.log(db=db, type_evenement="user_group_update", description=f"Modification du groupe '{groupe.nom}'")
        return groupe

    @staticmethod
    def supprimer(db: Session, groupe_id: int) -> None:
        groupe = db.query(UserGroup).get(groupe_id)
        if not groupe:
            raise ValueError("Groupe introuvable")

        db.delete(groupe)
        db.commit()
        HistoriqueService.log(db=db, type_evenement="user_group_delete", description=f"Suppression du groupe '{groupe.nom}'")
