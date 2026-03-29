from config.database import Base
from sqlalchemy import Column, Integer, String, Boolean,DATE
from enum import Enum

class UserRole(str,Enum):
    admin = "admin"
    operateur = "operateur"
    client = "client"

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,index=True)
    username=Column(String,unique=True)
    password=Column(String)
    first_name=Column(String)
    last_name=Column(String,nullable=True)
    email=Column(String)
    role=Column(Enum(UserRole),default=UserRole.client)
    date_of_born=Column(DATE)
    is_active=Column(Boolean,default=False)
    adress=Column(String,nullable=True)
    date_expire=Column(DATE,nullable=True)
    