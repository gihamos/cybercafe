from config.database import Base
from sqlalchemy import Column, Integer, Float,String, Boolean,Date,ForeignKey, Enum as SqlEnum,DateTime
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
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

    forfait_id = Column(Integer, ForeignKey("offre.id"), nullable=True)

    # Relation ORM
    forfait = relationship("Offre", backref="users")