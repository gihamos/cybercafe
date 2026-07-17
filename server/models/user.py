from config.database import Base
from sqlalchemy import (
    Column, Integer, Float, String, ForeignKey, Table,
    Boolean, Date, Enum as SqlEnum, DateTime, JSON
)
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime, date
from models.abonnement import Abonnement
from models.achat import Achat
from models.user_group import UserGroup


user_group_members = Table(
    "user_group_members",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("groupe_id", Integer, ForeignKey("user_groups.id"), primary_key=True),
)


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

    # Permissions granulaires pour un opérateur (voir services/permission_service.py) :
    # NULL = accès complet par défaut (comportement historique, rétrocompatible), sinon
    # liste explicite des clés de PERMISSIONS auxquelles cet opérateur a droit. Ignoré
    # pour les admins (accès total inconditionnel) et les clients (aucun accès staff).
    permissions = Column(JSON, nullable=True)

    solde_euros = Column(Float, default=0)

    # Quota de stockage réseau en Mo. NULL = utilise le défaut système
    # (voir system_setting "stockage.quota_defaut_mo"), sinon surcharge par utilisateur.
    quota_stockage_mo = Column(Float, nullable=True)

    # Nombre max de sessions actives simultanées pour ce compte, tous canaux confondus
    # (poste kiosque + WiFi, quel que soit le ticket/abonnement utilisé). NULL = 1
    # (comportement historique : une seule session à la fois) — contrairement aux
    # autres quotas de ce fichier, NULL ne veut PAS dire illimité ici : un système
    # d'accès payant ne doit jamais basculer en illimité par défaut, seulement si un
    # admin l'a explicitement configuré. Voir services/portail_service.py::verifier_limite_sessions.
    max_sessions_simultanees = Column(Integer, nullable=True)

    date_of_born = Column(Date, nullable=True)
    is_active = Column(Boolean, default=False)

    address = Column(String, nullable=True)

    date_create = Column(DateTime, default=datetime.utcnow)
    date_expire = Column(DateTime, nullable=True)

    # Pièce d'identité (conformité, comme dans les logiciels cybercafé de référence).
    # piece_identite_type reste une chaîne libre en base (pas de SqlEnum) — la liste
    # fermée (carte d'identité/passeport/permis/titre de séjour, voir TypePieceIdentite
    # ci-dessous) n'est imposée qu'au niveau du schéma Pydantic, pour ne pas casser sur
    # d'éventuelles valeurs déjà enregistrées hors de cette liste.
    piece_identite_type = Column(String, nullable=True)
    piece_identite_numero = Column(String, nullable=True)
    piece_identite_organisme = Column(String, nullable=True)
    piece_identite_expiration = Column(Date, nullable=True)
    # Scan/photo du document, stocké via services/storage_provider/ (voir router/user.py)
    piece_identite_cle_stockage = Column(String, nullable=True)
    piece_identite_content_type = Column(String, nullable=True)

    # Photo de profil, même mécanisme de stockage que la pièce d'identité
    photo_profil_cle_stockage = Column(String, nullable=True)
    photo_profil_content_type = Column(String, nullable=True)

    notes = Column(String, nullable=True)

    # Un client peut appartenir à plusieurs groupes simultanément (ex: "Étudiants" +
    # "VIP") — chaque groupe apporte ses propres limites (bande passante, filtrage de
    # contenu), fusionnées à la résolution (voir services/user_group_service.py).
    groupes = relationship("UserGroup", secondary=user_group_members, back_populates="membres")

    # Relations
    achat_offres = relationship(
        "Achat",
        back_populates="user",
        foreign_keys="Achat.user_id",overlaps="achats"
    )

    # Charte / conditions d'utilisation : date d'acceptation (NULL = jamais acceptée)
    charte_acceptee_le = Column(DateTime, nullable=True)

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


def get_age(user: User) -> int | None:
    """Âge en années pleines, ou None si la date de naissance est inconnue (ex:
    tickets anonymes) — utilisé par les règles de filtrage de contenu avec âge
    minimum (voir SiteRegle.age_min)."""
    if not user.date_of_born:
        return None
    today = date.today()
    dob = user.date_of_born
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


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
