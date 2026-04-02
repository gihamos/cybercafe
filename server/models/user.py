from config.database import Base
from sqlalchemy import (
    Column, Integer, Float, String, ForeignKey,
    Boolean, Date, Enum as SqlEnum, DateTime
)
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from models.abonnement import Abonnement
from models.achat import Achat


class UserRole(str, Enum):
    admin = "admin"
    operateur = "operateur"
    client = "client"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)

    email = Column(String, unique=True, nullable=False)

    role = Column(SqlEnum(UserRole), default=UserRole.client, nullable=False)

    solde_euros = Column(Float, default=0)

    date_of_born = Column(Date, nullable=True)
    is_active = Column(Boolean, default=False)

    address = Column(String, nullable=True)

    date_create = Column(DateTime, default=datetime.utcnow)
    date_expire = Column(DateTime, nullable=True)

    # Relations
    achat_offres = relationship(
        "Achat",
        back_populates="user",
        foreign_keys="Achat.user_id"
    )

    current_abonnement_id = Column(
        Integer,
        ForeignKey("abonnements.id"),
        nullable=True
    )

    current_abonnement = relationship(
        "Abonnement",
        foreign_keys=[current_abonnement_id],
        post_update=True
    )


def is_validUser(user: User) -> dict[str, any]:
    """Vérifie si un utilisateur est valide pour se connecter."""

    if not user.is_active:
        return {
            "valide": False,
            "detail": f"Le compte de {user.first_name} est désactivé."
        }

    if user.date_expire and user.date_expire < datetime.utcnow():
        return {
            "valide": False,
            "detail": f"Le compte de {user.first_name} a expiré le {user.date_expire.date()}."
        }

    return {
        "valide": True,
        "detail": "Le compte est valide."
    }
