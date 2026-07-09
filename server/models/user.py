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
from models.user_group import UserGroup


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

    # Quota de stockage réseau en Mo. NULL = utilise le défaut système
    # (voir system_setting "stockage.quota_defaut_mo"), sinon surcharge par utilisateur.
    quota_stockage_mo = Column(Float, nullable=True)

    date_of_born = Column(Date, nullable=True)
    is_active = Column(Boolean, default=False)

    address = Column(String, nullable=True)

    date_create = Column(DateTime, default=datetime.utcnow)
    date_expire = Column(DateTime, nullable=True)

    # Pièce d'identité (conformité, comme dans les logiciels cybercafé de référence)
    piece_identite_type = Column(String, nullable=True)
    piece_identite_numero = Column(String, nullable=True)
    piece_identite_organisme = Column(String, nullable=True)

    notes = Column(String, nullable=True)

    groupe_id = Column(Integer, ForeignKey("user_groups.id"), nullable=True)
    groupe = relationship("UserGroup", back_populates="users")

    # Relations
    achat_offres = relationship(
        "Achat",
        back_populates="user",
        foreign_keys="Achat.user_id",overlaps="achats"
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
