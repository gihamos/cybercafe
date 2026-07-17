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

    # Portail WiFi : fil de discussion par utilisateur. NULL = fil de poste classique
    # (kiosque) ; renseigné = fil WiFi du client, rattaché au poste virtuel Borne WiFi.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", foreign_keys=[user_id])

    # Portail WiFi en mode ticket (anonyme, sans compte) : fil de discussion par
    # SESSION plutôt que par utilisateur — pour économiser l'espace, ce fil est
    # éphémère (purgé à la fin de la session, voir SessionService.fermer_session)
    # sauf si un opérateur le marque à conserver (`conserver=True`, tous les messages
    # du fil à la fois — voir ChatService.marquer_conserver).
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    session = relationship("Session", foreign_keys=[session_id])
    conserver = Column(Boolean, default=False)

    expediteur = Column(SqlEnum(ExpediteurChat), nullable=False)

    # Renseigné seulement si expediteur == OPERATEUR
    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User", foreign_keys=[operateur_id])

    message = Column(String, nullable=False)
    date_envoi = Column(DateTime, default=datetime.utcnow)
    lu = Column(Boolean, default=False)

    # Pièce jointe optionnelle (un fichier par message) — voir services/chat_service.py.
    # Écrite via le même storage_provider que l'espace de stockage réseau, mais hors
    # quota utilisateur : la limite est uniquement une taille max par fichier
    # (configuration cybercafe "chat.taille_max_fichier_mo").
    piece_jointe_nom = Column(String, nullable=True)
    piece_jointe_cle = Column(String, nullable=True)
    piece_jointe_taille_octets = Column(Integer, nullable=True)
    piece_jointe_content_type = Column(String, nullable=True)
