from config.database import Base
from sqlalchemy import Column, Integer, Float,String,ForeignKey, Boolean,Date, Enum as SqlEnum,DateTime
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from server.models.abonnement import Abonnement
from models.offre import Offre


class UserRole(str,Enum):
    admin = "admin"
    operateur = "operateur"
    client = "client"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)

    first_name = Column(String)
    last_name = Column(String, nullable=True)
    email = Column(String)

    role = Column(SqlEnum(UserRole), default=UserRole.client)
    solde_euros=Column(Float,default=0)

    date_of_born = Column(Date)
    is_active = Column(Boolean, default=False)


    address = Column(String, nullable=True)
    date_create=Column(DateTime,default=datetime.today())
    date_expire = Column(DateTime, nullable=True)
    achat_offres = relationship(
        "AchatOffre",
        back_populates="user",
        foreign_keys="AchatOffre.user_id"  
    )
    current_abonnement_id = Column(
        Integer,
        ForeignKey("achat_offres.id"),
        nullable=True
    )
    current_abonnement = relationship(
        "Abonnement",
        foreign_keys=[current_abonnement_id],  #
        post_update=True
    )
    
    
def is_validUser(user:User)->dict[str,any]:
    """_summary_

    Args:
        user (User): _description_

    Returns:
        dict[str,any]: _description_
    """
    
    if(not user.is_active):
        return {
        "valide":False,
        "detail":f"le compte l'utlisateur {user.first_name} est desactivé"
    }
    elif user.date_expire and user.date_expire<datetime.today():
         return {
            "valide":False,
            "detail":f"le compte l'utlisateur {user.first_name} a expiré depuis le {user.date_expire.date()}"
         }
         
    else:
      return{
           "valide":False,
           "detail":"le compte est valide"
          
      }
