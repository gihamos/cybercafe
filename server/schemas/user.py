from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date, datetime
from models.user import User

# ---------------------------
# User creation schema
# ---------------------------
class UserCreate(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    date_of_born: date
    is_active: bool = False
    address: Optional[str] = None
    date_expire: Optional[datetime] = None

    # -----------------------
    # Validators
    # -----------------------
    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Mot de passe trop court, au moins 6 caractères")
        return v

    @field_validator("date_of_born")
    def validate_age(cls, v):
        if v:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 12:
                raise ValueError("Utilisateur trop jeune (min 12 ans)")
        return v


# ---------------------------
# User update schema
# ---------------------------
class UserUpdate(BaseModel):
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_born: Optional[date] = None
    address: Optional[str] = None

    @field_validator("password")
    def validate_password(cls, v):
        if v and len(v) < 6:
            raise ValueError("Mot de passe trop court, au moins 6 caractères")
        return v

    @field_validator("date_of_born")
    def validate_age(cls, v):
        if v:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 12:
                raise ValueError("Utilisateur trop jeune (min 12 ans)")
        return v


# ---------------------------
# User filter schema
# ---------------------------
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


# ---------------------------
# Sort mapping
# ---------------------------
SORT_FIELDS = {
    "username": User.username,
    "email": User.email,
    "solde": User.solde_euros,
    "date_create": User.date_create,
}