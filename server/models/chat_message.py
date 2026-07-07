from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class ExpediteurChat(str, enum.Enum):
    CLIENT = "client"
    OPERATEUR = "operateur"


class ChatMessage(Base):
    """Message de discussion en direct entre un poste (client/ticket) et un opérateur.
    Le fil de discussion est identifié par poste_id : chaque poste a un historique
    continu, indépendant des sessions qui s'y succèdent."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=False)
    poste = relationship("Poste", backref="chat_messages")

    expediteur = Column(SqlEnum(ExpediteurChat), nullable=False)

    # Renseigné seulement si expediteur == OPERATEUR
    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User", foreign_keys=[operateur_id])

    message = Column(String, nullable=False)
    date_envoi = Column(DateTime, default=datetime.utcnow)
    lu = Column(Boolean, default=False)
