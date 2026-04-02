from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from models.user import UserRole


# ---------------------------------------------------------
# BASE (champs communs)
# ---------------------------------------------------------
class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    role: UserRole = UserRole.client
    date_of_born: Optional[date] = None
    address: Optional[str] = None


# ---------------------------------------------------------
# CRÉATION D’UN USER
# ---------------------------------------------------------
class UserCreate(UserBase):
    password: str
    solde_initial: float = 0
    is_active: bool = False
    date_expire: Optional[datetime] = None


# ---------------------------------------------------------
# MISE À JOUR D’UN USER
# ---------------------------------------------------------
class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    date_of_born: Optional[date] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None
    date_expire: Optional[datetime] = None


# ---------------------------------------------------------
# RÉPONSE API (lecture)
# ---------------------------------------------------------
class UserResponse(UserBase):
    id: int
    solde_euros: float
    is_active: bool
    date_create: datetime
    date_expire: Optional[datetime]

    class Config:
        orm_mode = True


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
