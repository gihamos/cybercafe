from sqlalchemy.orm import Session

from models.user import User, UserRole
from services.historique_service import HistoriqueService

# Catalogue des permissions assignables à un opérateur. Chaque clé correspond à un
# module fonctionnel entier (mêmes regroupements que la navigation du panneau
# d'administration) plutôt qu'à une action isolée, pour rester lisible et gérable
# depuis l'écran Équipe. Un admin a toujours accès à tout, quel que soit ce catalogue.
#
# Deux familles, avec une sémantique de défaut opposée (voir verifier()) :
# - PERMISSIONS (opt-out) : accès complet par défaut pour un opérateur non restreint
#   (permissions=None) — l'admin les RETIRE explicitement pour restreindre. Couvre les
#   tâches courantes d'un opérateur : vendre (tickets/forfaits/articles), encaisser,
#   surveiller les postes, répondre au chat.
# - PERMISSIONS_AVANCEES (opt-in) : refusées par défaut à un opérateur, même non
#   restreint — l'admin les AJOUTE explicitement pour déléguer une tâche qui relève
#   normalement de lui (gestion de stock, création de forfaits). Jamais implicites.
PERMISSIONS: dict[str, str] = {
    "postes": "Gérer les postes (verrouiller, déverrouiller, commandes, réveil)",
    "caisse": "Opérer la caisse (ouvrir, encaisser, clôturer)",
    "clients": "Gérer les groupes de clients",
    "catalogue": "Vendre le catalogue (tickets, forfaits, articles) et gérer les promotions",
    "chat": "Répondre aux clients dans le chat",
    "bande_passante": "Gérer la bande passante et le filtrage de contenu",
    "surveillance": "Consulter les captures d'écran et l'historique de navigation des postes",
}

PERMISSIONS_AVANCEES: dict[str, str] = {
    "gestion_stock": "Gérer le stock des articles — réapprovisionnement, ajustements (délégué par l'administrateur, désactivé par défaut)",
    "creation_forfaits": "Créer et modifier les forfaits/offres (délégué par l'administrateur, désactivé par défaut)",
}

# Catalogue complet exposé au panneau d'administration (une seule liste de cases à
# cocher) — la distinction opt-out/opt-in n'affecte que verifier(), pas l'affichage.
PERMISSIONS_TOUTES: dict[str, str] = {**PERMISSIONS, **PERMISSIONS_AVANCEES}


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

        if cle in PERMISSIONS_AVANCEES:
            # Opt-in : jamais incluse dans l'accès complet implicite (permissions=None),
            # il faut que l'admin l'ait explicitement ajoutée à la liste de l'opérateur.
            return user.permissions is not None and cle in user.permissions

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
            inconnues = [p for p in permissions if p not in PERMISSIONS_TOUTES]
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
