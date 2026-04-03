from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime

from models.user import User, UserRole, is_validUser
from models.paiement import Paiement, TypePaiement
from models.recharge_solde import RechargeSolde

from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from models.notification import TypeNotification
from schemas.user_schema import SORT_FIELDS
from models.historique import TypeEvenement


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
        HistoriqueService.log(
            db=db,
        type_evenement=TypeEvenement.CONNEXION,
        description=f"connexion avec success pour le user {user.username}",
        user_id=user.id,
        details={"nouveau_solde": user.solde_euros}
       )
        NotificationService.send_to_user(
        db=db,
      user_id=user.id,
      titre="connexion avec succèes",
       message=f"Vous vous etes connecté avec succès le {datetime.utcnow()}",
       type_notification=TypeNotification.INFO
      )

        return user

    # ---------------------------------------------------------
    # CRÉATION D’UN UTILISATEUR
    # ---------------------------------------------------------
    @staticmethod
    def create_user(db: Session, data:dict[str,any]):
        # Vérification unicité username/email
        if db.query(User).filter(User.username == data.get("username")).first():
            raise ValueError("Nom d'utilisateur déjà utilisé")

        if db.query(User).filter(User.email == data.get("email")).first():
            raise ValueError("Email déjà utilisé")
        
        data["password"]=hash_password(data["password"])
        data["username"]=str(data["username"]).lower()
        data["email"]=str(data["email"]).lower()

        user = User(**data)

        db.add(user)
        db.commit()
        db.refresh(user)

        HistoriqueService.log(
            db=db,
            type_evenement=TypeEvenement.ACTION_OPERATEUR,
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
    def update_user(db: Session,  user_iden: int|str, data):
        query = db.query(User)
        if str(user_iden).isdigit():
            user = query.filter(
        User.id == int(user_iden)
        ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(or_(User.username == user_iden,User.email==user_iden)).first()
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
        
        user.email=str(user.email).lower()

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement=TypeEvenement.AUTRE,
            description=f"Mise à jour du profil de {user.username}",
            user_id=user.id,
            details=updated_fields
        )

        return user

    # ---------------------------------------------------------
    # GESTION DU SOLDE : RECHARGE
    # ---------------------------------------------------------
    @staticmethod
    def ajouter_solde(db: Session,  user_iden: int|str, montant: float, type_paiement: TypePaiement):
        query = db.query(User)
        if str(user_iden).isdigit():
            user = query.filter(
        User.id == int(user_iden)
        ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(or_(User.username == user_iden,User.email==user_iden)).first()
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
            type_evenement=TypeEvenement.ACHAT,
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
    def retirer_solde(db: Session, user_iden: str|int, montant: float):
        query = db.query(User)
        if str(user_iden).isdigit():
            user = query.filter(
                User.id == int(user_iden)
            ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(or_(User.username == user_iden,User.email==user_iden)).first()
            
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
            type_evenement=TypeEvenement.CONSOMMATION,
            description=f"Débit de {montant}€ pour {user.username}",
            user_id=user.id,
            details={"nouveau_solde": user.solde_euros}
        )

        return user.solde_euros

    # ---------------------------------------------------------
    # ACTIVATION / DÉSACTIVATION
    # ---------------------------------------------------------
    @staticmethod
    def set_active(db: Session, user_iden: str|int, active: bool):
        query = db.query(User)
        if str(user_iden).isdigit():
            user = query.filter(
            User.id == int(user_iden)
        ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(
                or_(User.username == user_iden , User.email==user_iden)).first()
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
    
    @staticmethod
    def update_expire_date(db: Session, user_iden: str|int, expire_date: datetime):
     query = db.query(User)
     if str(user_iden).isdigit():
        user = query.filter(
        User.id == int(user_iden),
        ).first()
     else:
        user_iden=str(user_iden).lower()
        user = query.filter(
            or_(User.username == user_iden , User.email==user_iden)).first()
     if not user:
         raise ValueError("Utilisateur introuvable")
     user.date_expire = expire_date
     db.commit()
     
     HistoriqueService.log(
         db=db,
         type_evenement="update_date_expiration",
         description=f"Changement de la date d'expiration du compte {user.username} pour le {user.date_expire}",
         user_id=user.id
     )
     NotificationService.send_to_user(
         db=db,
         user_id=user.id,
         titre="Changement d'état du compte",
         message=f"la date d'expiration de Votre compte a été modifié. votre compte exiprera le {user.date_expire}",
         type_notification=TypeNotification.SYSTEM
     )
     return user
 
    @staticmethod
    def update_role(db: Session, user_iden: str|int, role: UserRole):
        query = db.query(User)
        if str(user_iden).isdigit():
            user = query.filter(
            User.id == int(user_iden),
            ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(
         or_(User.username == user_iden , User.email==user_iden)).first()
        if not user:
            raise ValueError("Utilisateur introuvable")
        ancien_role=user.role
        user.role = role
        db.commit()
        db.refresh(user)
  
        HistoriqueService.log(
        db=db,
        type_evenement="update_role",
        description=f"Changement du role {ancien_role} du compte {user.username} pour le role {user.role}",
        user_id=user.id
        )
        NotificationService.send_to_user(
        db=db,
       user_id=user.id,
       titre="attribution d'un nouveau role",
       message=f" un nouveau role vous a été attribué: {user.role} précedement vous avez le role {ancien_role}",
       type_notification=TypeNotification.SYSTEM
        )
        return user

    # ---------------------------------------------------------
    # SUPPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def delete_user(db: Session, user_iden: int|str):
        query = db.query(User)

        if str(user_iden).isdigit():
            user = query.filter(
            
                User.id == int(user_iden)
            
        ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(or_(User.username == user_iden,User.email==user_iden)).first()
            
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
    
    @staticmethod
    def setUpdateCompte(
    user_iden: str|int,
    currentuser:User,
    db: Session,
    active:bool=None,
    exipredate:datetime=None,
   
   
    ):
    
        if active is None and exipredate is None:
            raise ValueError("Il faut au moins active ou exipredate")
        query = db.query(User)
        if str(user_iden).isdigit():
            user = query.filter(
     
                User.id == int(user_iden)
     
            ).first()
        else:
            user_iden=str(user_iden).lower()
            user = query.filter(or_(User.username == user_iden,User.email==user_iden)).first()
     
        if not user:
     
            raise ValueError("Utilisateur introuvable")
        if (UserRole(currentuser.role)==UserRole.operateur) and (UserRole(user.role)==UserRole.operateur or UserRole(user.role)==UserRole.admin):
            raise ValueError(f" vous avez pas le droit de faire cet opération sur l'utlisateur : {user.username} ")
        
        if active is not None:
          user=UserService.set_active(db=db,user_iden=user_iden,active=active)
          
        if exipredate is not None:
            user=UserService.update_expire_date(db=db,user_iden=user_iden,expire_date=exipredate)
            
        return user
        

 
