from sqlalchemy.orm import Session

from models.user import User, UserRole
from services.historique_service import HistoriqueService

# Catalogue des permissions assignables à un opérateur. Chaque clé correspond à un
# module fonctionnel entier (mêmes regroupements que la navigation du panneau
# d'administration) plutôt qu'à une action isolée, pour rester lisible et gérable
# depuis l'écran Équipe. Un admin a toujours accès à tout, quel que soit ce catalogue.
PERMISSIONS: dict[str, str] = {
    "postes": "Gérer les postes (verrouiller, déverrouiller, commandes, réveil)",
    "caisse": "Opérer la caisse (ouvrir, encaisser, clôturer)",
    "clients": "Gérer les groupes de clients",
    "catalogue": "Gérer le catalogue (promotions, tickets, réappro. articles)",
    "chat": "Répondre aux clients dans le chat",
    "bande_passante": "Gérer la bande passante et le filtrage de contenu",
    "surveillance": "Consulter les captures d'écran et l'historique de navigation des postes",
}


class PermissionService:

    @staticmethod
    def get_permissions_effectives(db: Session, user_id: int) -> list[str] | None:
        """None = accès complet (défaut historique ou admin), sinon liste explicite."""
        user = db.query(User).get(user_id)
        if not user:
            return []
        if user.role == UserRole.admin:
            return None
        return user.permissions

    @staticmethod
    def verifier(db: Session, user_id: int, role: str, cle: str) -> bool:
        if UserRole(role) == UserRole.admin:
            return True
        if UserRole(role) != UserRole.operateur:
            return False

        user = db.query(User).get(user_id)
        if not user:
            return False
        if user.permissions is None:
            return True  # pas de restriction explicite = accès complet (rétrocompatible)
        return cle in user.permissions

    @staticmethod
    def set_permissions(db: Session, user_id: int, permissions: list[str] | None, operateur_id: int | None = None) -> User:
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")
        if user.role != UserRole.operateur:
            raise ValueError("Les permissions ne s'appliquent qu'aux opérateurs")

        if permissions is not None:
            inconnues = [p for p in permissions if p not in PERMISSIONS]
            if inconnues:
                raise ValueError(f"Permission(s) inconnue(s) : {', '.join(inconnues)}")

        user.permissions = permissions
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="permissions_update",
            description=f"Permissions de {user.username} mises à jour",
            user_id=user_id,
            operateur_id=operateur_id,
            details={"permissions": permissions},
        )
        return user
