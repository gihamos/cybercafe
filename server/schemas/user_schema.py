from pydantic import BaseModel, EmailStr,field_validator
from typing import Optional
from datetime import date, datetime
from models.user import UserRole,User


# Liste fermée pour les nouvelles saisies (voir models/user.py::piece_identite_type
# pour pourquoi la colonne elle-même reste une chaîne libre en base).
TYPES_PIECE_IDENTITE = ["carte_identite", "passeport", "permis_conduire", "titre_sejour"]


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class UserBase(BaseModel):
    password: Optional[str] = None
    last_name: Optional[str] = None
    date_of_born: Optional[date] = None
    address: Optional[str] = None
    date_expire: Optional[datetime] = None
    piece_identite_type: Optional[str] = None
    piece_identite_numero: Optional[str] = None
    piece_identite_organisme: Optional[str] = None
    piece_identite_expiration: Optional[date] = None
    notes: Optional[str] = None
    # Sessions actives simultanées max pour ce compte, tous canaux confondus.
    # None = 1 (voir models/user.py::max_sessions_simultanees pour le raisonnement).
    max_sessions_simultanees: Optional[int] = None


    @field_validator("date_of_born")
    def validate_age(cls, v):
     if v:
         today = date.today()
         age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
         if age < 12:
             raise ValueError("Utilisateur trop jeune (min 12 ans)")
     return v


    @field_validator("password")
    def validate_password(cls, v):
        if v and len(v) < 4:
          raise ValueError("Mot de passe trop court, au moins 4 caractères")
        return v

    @field_validator("piece_identite_type")
    def validate_type_piece(cls, v):
        if v and v not in TYPES_PIECE_IDENTITE:
            raise ValueError(f"Type de pièce d'identité invalide (valeurs autorisées : {', '.join(TYPES_PIECE_IDENTITE)})")
        return v


# ---------------------------------------------------------
# CRÉATION D’UN USER
# ---------------------------------------------------------
class UserCreate(UserBase):
    username: str
    first_name: str
    email: EmailStr
    role: UserRole = UserRole.client
    password: str
    is_active: bool = False
   
    


# ---------------------------------------------------------
# MISE À JOUR D’UN USER
# ---------------------------------------------------------
class UserUpdate(UserBase):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    adress : Optional[str] = None


class PermissionsUpdate(BaseModel):
    # None = accès complet (pas de restriction), [] = aucune permission, sinon la liste
    # explicite des clés autorisées (voir services/permission_service.py::PERMISSIONS)
    permissions: Optional[list[str]] = None



# ---------------------------------------------------------
# RÉPONSE API (lecture)
# ---------------------------------------------------------
class UserResponse(BaseModel):
    id: Optional[int]=None
    username:Optional[str]=None
    email:Optional[str]=None
    first_name: Optional[str]=None
    last_name: Optional[str]=None
    solde_euros: Optional[float]=None
    is_active: Optional[bool]=None
    date_create: Optional[datetime]=None
    date_expire: Optional[datetime]=None
    address:Optional[str]=None
    piece_identite_type: Optional[str] = None
    piece_identite_numero: Optional[str] = None
    piece_identite_organisme: Optional[str] = None
    piece_identite_expiration: Optional[date] = None
    a_une_piece_identite: Optional[bool] = None
    a_une_photo: Optional[bool] = None
    notes: Optional[str] = None
    groupe_ids: Optional[list[int]] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# RÉPONSE AUTHENTIFICATION
# ---------------------------------------------------------
class UserLogin(BaseModel):
    username: str
    password: str


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    class Config:
        orm_mode = True


class UserGroupCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    mode_filtrage: Optional[str] = None
    quota_stockage_mo: Optional[float] = None


class UserGroupUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    mode_filtrage: Optional[str] = None
    quota_stockage_mo: Optional[float] = None


SORT_FIELDS = {
    "username": User.username,
    "email": User.email,
    "solde": User.solde_euros,
    "date_create": User.date_create,
}


class UserFilter(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    min_solde: Optional[float] = None
    max_solde: Optional[float] = None
    date_created_after: Optional[datetime] = None
    date_created_before: Optional[datetime] = None


    # Pagination & sorting
    limit: Optional[int] = 10
    offset: Optional[int] = 0
    sort_by: Optional[str] = None


    # -----------------------
    # Validators
    # -----------------------
    @field_validator("max_solde")
    def validate_solde(cls, v, info):
        min_solde = info.data.get("min_solde")
        if v is not None and min_solde is not None and v < min_solde:
            raise ValueError("max_solde doit être >= min_solde")
        return v


    @field_validator("limit")
    def validate_limit(cls, v):
        if v is not None and v <= 0:
            raise ValueError("limit doit être > 0")
        return v


    @field_validator("offset")
    def validate_offset(cls, v):
        if v is not None and v < 0:
            raise ValueError("offset doit être >= 0")
        return v