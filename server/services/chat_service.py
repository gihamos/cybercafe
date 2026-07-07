from sqlalchemy.orm import Session
from sqlalchemy import func

from models.chat_message import ChatMessage, ExpediteurChat
from models.poste import Poste
from services.historique_service import HistoriqueService


class ChatService:

    @staticmethod
    def _get_poste(db: Session, poste_id: int) -> Poste:
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")
        return poste

    @staticmethod
    def envoyer_message_client(db: Session, poste_id: int, message: str) -> ChatMessage:
        ChatService._get_poste(db, poste_id)

        msg = ChatMessage(
            poste_id=poste_id,
            expediteur=ExpediteurChat.CLIENT,
            message=message,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        HistoriqueService.log(
            db=db,
            type_evenement="chat_message",
            description=f"Message du poste {poste_id} vers l'opérateur",
            poste_id=poste_id,
        )
        return msg

    @staticmethod
    def envoyer_message_operateur(db: Session, poste_id: int, operateur_id: int, message: str) -> ChatMessage:
        ChatService._get_poste(db, poste_id)

        msg = ChatMessage(
            poste_id=poste_id,
            expediteur=ExpediteurChat.OPERATEUR,
            operateur_id=operateur_id,
            message=message,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        HistoriqueService.log(
            db=db,
            type_evenement="chat_message",
            description=f"Message de l'opérateur vers le poste {poste_id}",
            operateur_id=operateur_id,
            poste_id=poste_id,
        )
        return msg

    @staticmethod
    def historique(db: Session, poste_id: int, limit: int = 200) -> list[ChatMessage]:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.poste_id == poste_id)
            .order_by(ChatMessage.date_envoi.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def compter_non_lus_par_poste(db: Session) -> dict[int, int]:
        """Nombre de messages CLIENT non lus, groupés par poste — utilisé par le
        panneau d'administration pour afficher un badge de messages en attente."""
        rows = (
            db.query(ChatMessage.poste_id, func.count(ChatMessage.id))
            .filter(ChatMessage.expediteur == ExpediteurChat.CLIENT, ChatMessage.lu == False)
            .group_by(ChatMessage.poste_id)
            .all()
        )
        return {poste_id: count for poste_id, count in rows}

    @staticmethod
    def marquer_lu(db: Session, poste_id: int, expediteur_a_marquer: ExpediteurChat) -> None:
        """Marque comme lus les messages envoyés par `expediteur_a_marquer` (ex: appelé côté
        admin avec ExpediteurChat.CLIENT pour marquer les messages du client comme lus)."""
        (
            db.query(ChatMessage)
            .filter(ChatMessage.poste_id == poste_id, ChatMessage.expediteur == expediteur_a_marquer, ChatMessage.lu == False)
            .update({"lu": True})
        )
        db.commit()
