from sqlalchemy import Column, Integer, String
from config.database import Base
from enum import Enum


class PosteEtat(str,Enum):
    libre = "libre"
    occupe = "occupe"
    bloquer = "bloquer"

class Poste(Base):
    __tablename__ = "postes"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    etat = Column(Enum(PosteEtat), default=PosteEtat.bloquer)  # libre, occupe, bloque
    ip = Column(String, nullable=True)
    mac_adress=Column(String,nullable=True)