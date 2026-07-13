import io
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.chat_message import ChatMessage, ExpediteurChat
from models.poste import Poste
from services.historique_service import HistoriqueService
from services.storage_provider import get_provider
from services.config_service import ConfigService
from params import STORAGE_PROVIDER


class ChatService:

    @staticmethod
    def _get_poste(db: Session, poste_id: int) -> Poste:
        poste = db.query(Poste).get(poste_id)
        if not poste:
            raise ValueError("Poste introuvable")
        return poste

    # ---------------------------------------------------------
    # PIÈCES JOINTES
    # ---------------------------------------------------------
    @staticmethod
    def taille_max_fichier_octets(db: Session) -> int:
        taille_mo = ConfigService.get_config(db).get("chat.taille_max_fichier_mo") or 5
        return int(float(taille_mo) * 1024 * 1024)

    @staticmethod
    def _stocker_piece_jointe(db: Session, poste_id: int, contenu: bytes, nom_original: str) -> str:
        limite = ChatService.taille_max_fichier_octets(db)
        if len(contenu) > limite:
            raise ValueError(f"Fichier trop volumineux (limite : {limite // (1024 * 1024)} Mo)")

        provider = get_provider(STORAGE_PROVIDER)
        cle = f"chat/poste_{poste_id}/{uuid.uuid4().hex}_{nom_original}"
        provider.upload(cle, io.BytesIO(contenu))
        return cle

    @staticmethod
    def get_piece_jointe(db: Session, message_id: int) -> tuple[ChatMessage, io.BufferedIOBase]:
        msg = db.query(ChatMessage).get(message_id)
        if not msg or not msg.piece_jointe_cle:
            raise ValueError("Pièce jointe introuvable")

        provider = get_provider(STORAGE_PROVIDER)
        return msg, provider.download(msg.piece_jointe_cle)

    @staticmethod
    def envoyer_message_client(
        db: Session, poste_id: int, message: str,
        fichier: tuple[bytes, str, str | None] | None = None,
    ) -> ChatMessage:
        ChatService._get_poste(db, poste_id)

        msg = ChatMessage(
            poste_id=poste_id,
            expediteur=ExpediteurChat.CLIENT,
            message=message,
        )
        if fichier:
            contenu, nom_original, content_type = fichier
            msg.piece_jointe_cle = ChatService._stocker_piece_jointe(db, poste_id, contenu, nom_original)
            msg.piece_jointe_nom = nom_original
            msg.piece_jointe_taille_octets = len(contenu)
            msg.piece_jointe_content_type = content_type

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
    def envoyer_message_operateur(
        db: Session, poste_id: int, operateur_id: int, message: str,
        fichier: tuple[bytes, str, str | None] | None = None,
    ) -> ChatMessage:
        ChatService._get_poste(db, poste_id)

        msg = ChatMessage(
            poste_id=poste_id,
            expediteur=ExpediteurChat.OPERATEUR,
            operateur_id=operateur_id,
            message=message,
        )
        if fichier:
            contenu, nom_original, content_type = fichier
            msg.piece_jointe_cle = ChatService._stocker_piece_jointe(db, poste_id, contenu, nom_original)
            msg.piece_jointe_nom = nom_original
            msg.piece_jointe_taille_octets = len(contenu)
            msg.piece_jointe_content_type = content_type

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
            .filter(ChatMessage.poste_id == poste_id, ChatMessage.user_id == None)
            .order_by(ChatMessage.date_envoi.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def compter_non_lus_par_poste(db: Session) -> dict[int, int]:
        """Nombre de messages CLIENT non lus, groupés par poste — utilisé par le
        panneau d'administration pour afficher un badge de messages en attente.
        Les fils WiFi (user_id renseigné) sont comptés à part, voir compter_non_lus_wifi."""
        rows = (
            db.query(ChatMessage.poste_id, func.count(ChatMessage.id))
            .filter(
                ChatMessage.expediteur == ExpediteurChat.CLIENT,
                ChatMessage.lu == False,
                ChatMessage.user_id == None,
            )
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
            .filter(
                ChatMessage.poste_id == poste_id,
                ChatMessage.user_id == None,
                ChatMessage.expediteur == expediteur_a_marquer,
                ChatMessage.lu == False,
            )
            .update({"lu": True})
        )
        db.commit()

    # ---------------------------------------------------------
    # FILS WIFI (portail) — un fil de discussion par utilisateur, rattaché au poste
    # virtuel Borne WiFi. Mêmes règles que les fils de poste, mais identifiés par
    # user_id.
    # ---------------------------------------------------------
    @staticmethod
    def envoyer_message_wifi(
        db: Session, user_id: int, message: str,
        expediteur: ExpediteurChat = ExpediteurChat.CLIENT,
        operateur_id: int | None = None,
    ) -> ChatMessage:
        from services.portail_service import PortailService
        borne = PortailService.get_or_create_borne(db)

        msg = ChatMessage(
            poste_id=borne.id,
            user_id=user_id,
            expediteur=expediteur,
            operateur_id=operateur_id,
            message=message,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        HistoriqueService.log(
            db=db,
            type_evenement="chat_message",
            description=(
                f"Message WiFi de l'utilisateur {user_id} vers l'opérateur"
                if expediteur == ExpediteurChat.CLIENT
                else f"Message de l'opérateur vers l'utilisateur WiFi {user_id}"
            ),
            user_id=user_id,
            operateur_id=operateur_id,
        )
        return msg

    @staticmethod
    def historique_wifi(db: Session, user_id: int, limit: int = 200) -> list[ChatMessage]:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.date_envoi.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def threads_wifi(db: Session) -> list[dict]:
        """Fils WiFi pour le panneau d'administration : un par utilisateur ayant au
        moins un message, avec dernier message et nombre de non-lus côté client."""
        from models.user import User

        derniers = (
            db.query(
                ChatMessage.user_id,
                func.max(ChatMessage.date_envoi).label("dernier"),
                func.count(ChatMessage.id).label("total"),
            )
            .filter(ChatMessage.user_id != None)
            .group_by(ChatMessage.user_id)
            .all()
        )
        non_lus = dict(
            db.query(ChatMessage.user_id, func.count(ChatMessage.id))
            .filter(
                ChatMessage.user_id != None,
                ChatMessage.expediteur == ExpediteurChat.CLIENT,
                ChatMessage.lu == False,
            )
            .group_by(ChatMessage.user_id)
            .all()
        )
        threads = []
        for user_id, dernier, total in derniers:
            user = db.query(User).get(user_id)
            threads.append({
                "user_id": user_id,
                "username": user.username if user else f"#{user_id}",
                "dernier_message": dernier,
                "total": total,
                "non_lus": non_lus.get(user_id, 0),
            })
        threads.sort(key=lambda t: t["dernier_message"] or "", reverse=True)
        return threads

    @staticmethod
    def compter_non_lus_wifi(db: Session) -> int:
        return (
            db.query(func.count(ChatMessage.id))
            .filter(
                ChatMessage.user_id != None,
                ChatMessage.expediteur == ExpediteurChat.CLIENT,
                ChatMessage.lu == False,
            )
            .scalar() or 0
        )

    @staticmethod
    def marquer_lu_wifi(db: Session, user_id: int, expediteur_a_marquer: ExpediteurChat) -> None:
        (
            db.query(ChatMessage)
            .filter(
                ChatMessage.user_id == user_id,
                ChatMessage.expediteur == expediteur_a_marquer,
                ChatMessage.lu == False,
            )
            .update({"lu": True})
        )
        db.commit()
