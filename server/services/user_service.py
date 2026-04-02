from sqlalchemy.orm import Session
from datetime import datetime

from models.user import User, UserRole, is_validUser
from models.paiement import Paiement, TypePaiement
from server.models.recharge_solde import RechargeSolde

from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from models.notification import TypeNotification
from schemas.user_schema import SORT_FIELDS

from utils.security import hash_password,verify_password


class UserService:

    # ---------------------------------------------------------
    # AUTHENTIFICATION
    # ---------------------------------------------------------
    @staticmethod
    def authenticate(db: Session, username: str, password: str):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise ValueError("username ou de passe incorrect")

        if not verify_password(password, user.password):
            raise ValueError("username ou de passe incorrect")

        valid = is_validUser(user)
        if not valid["valide"]:
            raise ValueError(valid["detail"])

        return user

    # ---------------------------------------------------------
    # CRÉATION D’UN UTILISATEUR
    # ---------------------------------------------------------
    @staticmethod
    def create_user(db: Session, data):
        # Vérification unicité username/email
        if db.query(User).filter(User.username == data.username).first():
            raise ValueError("Nom d'utilisateur déjà utilisé")

        if db.query(User).filter(User.email == data.email).first():
            raise ValueError("Email déjà utilisé")

        user = User(
            username=data.username,
            password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            role=data.role,
            solde_euros=data.solde_initial,
            date_of_born=data.date_of_born,
            is_active=data.is_active,
            address=data.address,
            date_expire=data.date_expire,
            date_create=datetime.utcnow()
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        HistoriqueService.log(
            db=db,
            type_evenement="creation_user",
            description=f"Création du compte {user.username}",
            user_id=user.id
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user.id,
            titre="Bienvenue",
            message="Votre compte a été créé avec succès.",
            type_notification=TypeNotification.INFO
        )

        return user

    # ---------------------------------------------------------
    # MISE À JOUR DU PROFIL
    # ---------------------------------------------------------
    @staticmethod
    def update_user(db: Session, user_id: int, data):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        updated_fields = {}

        # Mot de passe
        if data.password:
            user.password = hash_password(data.password)
            updated_fields["password"] = True

        # Champs simples
        for field in ["first_name", "last_name", "email", "date_of_born", "address"]:
            value = getattr(data, field)
            if value is not None:
                setattr(user, field, value)
                updated_fields[field] = value

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="update_user",
            description=f"Mise à jour du profil de {user.username}",
            user_id=user.id,
            details=updated_fields
        )

        return user

    # ---------------------------------------------------------
    # GESTION DU SOLDE : RECHARGE
    # ---------------------------------------------------------
    @staticmethod
    def ajouter_solde(db: Session, user_id: int, montant: float, type_paiement: TypePaiement):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if montant <= 0:
            raise ValueError("Montant invalide")

        # Paiement
        paiement = Paiement(
            user_id=user.id,
            montant=montant,
            type_paiement=type_paiement,
            statut="succes"
        )
        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        # Recharge
        recharge = RechargeSolde(
            user_id=user.id,
            paiement_id=paiement.id,
            montant=montant
        )
        db.add(recharge)

        # Mise à jour solde
        user.solde_euros += montant
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="recharge_solde",
            description=f"Recharge de {montant}€ pour {user.username}",
            user_id=user.id,
            details={"nouveau_solde": user.solde_euros}
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user.id,
            titre="Recharge effectuée",
            message=f"Votre solde a été crédité de {montant}€.",
            type_notification=TypeNotification.PAIEMENT
        )

        return user.solde_euros

    # ---------------------------------------------------------
    # GESTION DU SOLDE : DÉBIT
    # ---------------------------------------------------------
    @staticmethod
    def retirer_solde(db: Session, user_id: int, montant: float):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if montant <= 0:
            raise ValueError("Montant invalide")

        if user.solde_euros < montant:
            raise ValueError("Solde insuffisant")

        user.solde_euros -= montant
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="debit_solde",
            description=f"Débit de {montant}€ pour {user.username}",
            user_id=user.id,
            details={"nouveau_solde": user.solde_euros}
        )

        return user.solde_euros

    # ---------------------------------------------------------
    # ACTIVATION / DÉSACTIVATION
    # ---------------------------------------------------------
    @staticmethod
    def set_active(db: Session, user_id: int, active: bool):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        user.is_active = active
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="activation_user" if active else "desactivation_user",
            description=f"Changement d'état du compte {user.username}",
            user_id=user.id
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user.id,
            titre="Changement d'état du compte",
            message="Votre compte a été activé." if active else "Votre compte a été désactivé.",
            type_notification=TypeNotification.SYSTEM
        )

        return user

    # ---------------------------------------------------------
    # SUPPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def delete_user(db: Session, user_id: int):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        db.delete(user)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="suppression_user",
            description=f"Suppression du compte {user.username}",
            user_id=user.id
        )

        return True
     
    @staticmethod
    def getuser(db: Session,filters: dict[str,any])->list[User]:
        
        if (filters.get("max_solde") and  filters.get("min_solde")) and (filters.get("max_solde") <filters.get("min_solde") ):
            raise ValueError("le solde maximun ne peut pas être plus petit que le solde minimun")
        
       
       
        
        query = db.query(User)
        if filters.get("role") is not None:
            query.filter(User.role==filters.get("role"))
            
        if filters.get("username"):
            query = query.filter(User.username.contains(filters.get("username")))
            
        if filters.get("email"):
            query = query.filter(User.email.contains(filters.get("email")))
            
        if filters.get("first_name"):
            query = query.filter(User.first_name.contains(filters.get("first_name")))
            
        if filters.get("is_active") is not None:
            query = query.filter(User.is_active == filters.get("is_active"))
            
        if filters.get("min_solde") is not None:
            query = query.filter(User.solde_euros >= filters.get("min_solde"))
            
        if filters.get("max_solde") is not None:
            query = query.filter(User.solde_euros <= filters.get("max_solde"))
            
        if filters.get("date_created_after"):
            query = query.filter(User.date_create >= filters.get("date_created_after"))
            
        if filters.get("date_created_before"):
            query = query.filter(User.date_create <= filters.date_created_before)

        if filters.get("sort_by"):
            field = SORT_FIELDS.get(filters.get("sort_by"))
            
            if not field:
                raise  ValueError("Champ de tri invalide")
     
            query = query.order_by(field)
            
        query = query.offset(filters.get("offset",0)).limit(filters.get("limit",10))
        users = query.all()
        return users
        