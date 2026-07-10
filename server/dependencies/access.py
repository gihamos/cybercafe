from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from models.user import UserRole
from config.database import get_db
from services.permission_service import PermissionService

def get_current_user(request: Request):
    user = getattr(request.state, "user", None)

    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non authentifié")

    if "role" not in user:
        raise HTTPException(status_code=400, detail="Rôle manquant dans le token")

    return user

def require_roles(allowed_roles: list[UserRole]):
    async def dependency(request: Request):
        user = get_current_user(request)

        local_role = UserRole(user["role"])

        if local_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Vous n'avez pas les droits"
            )

        return user

    return dependency

def require_permission(cle: str):
    """Vérifie qu'un opérateur a la permission `cle` (voir services/permission_service.py
    pour le catalogue). Les admins passent toujours. À utiliser EN PLUS de require_roles,
    pas à sa place : ne fait aucune vérification de rôle elle-même."""
    async def dependency(request: Request, db: Session = Depends(get_db)):
        user = get_current_user(request)
        if not PermissionService.verifier(db=db, user_id=user["id"], role=user["role"], cle=cle):
            raise HTTPException(status_code=403, detail=f"Permission manquante : {cle}")
        return user

    return dependency


def user_access_dependency():
    async def dependency(request: Request, username: str):
        user = get_current_user(request)

        local_role = UserRole(user["role"])

        #  admin peut tout faire
        if local_role == UserRole.admin:
            return user

        # user peut modifier son propre compte
        if user.get("username") == username:
            return user

        raise HTTPException(
            status_code=403,
            detail="Accès interdit"
        )

    return dependency