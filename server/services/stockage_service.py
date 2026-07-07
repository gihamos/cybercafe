import io
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.fichier_stocke import FichierStocke
from models.user import User
from models.ticket import Ticket
from services.storage_provider import get_provider
from services.system_setting_service import SystemSettingsService
from services.historique_service import HistoriqueService
from params import STORAGE_PROVIDER

QUOTA_DEFAUT_MO = 500.0
QUOTA_TICKET_MO = 100.0


class StockageService:

    # ---------------------------------------------------------
    # QUOTAS
    # ---------------------------------------------------------
    @staticmethod
    def get_quota_mo(db: Session, user_id: int) -> float:
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if user.quota_stockage_mo is not None:
            return user.quota_stockage_mo

        try:
            return float(SystemSettingsService.get_valeur(db, "stockage.quota_defaut_mo"))
        except ValueError:
            return QUOTA_DEFAUT_MO

    @staticmethod
    def set_quota(db: Session, user_id: int, quota_mo: float | None, operateur_id: int | None = None) -> User:
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        user.quota_stockage_mo = quota_mo
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="stockage_quota_update",
            description=f"Quota de stockage de {user.username} fixé à {quota_mo if quota_mo is not None else 'défaut'} Mo",
            user_id=user_id,
            operateur_id=operateur_id,
        )
        return user

    @staticmethod
    def get_usage_octets(db: Session, user_id: int | None = None, ticket_id: int | None = None) -> int:
        query = db.query(func.coalesce(func.sum(FichierStocke.taille_octets), 0))
        if user_id is not None:
            query = query.filter(FichierStocke.user_id == user_id)
        else:
            query = query.filter(FichierStocke.ticket_id == ticket_id)
        return query.scalar() or 0

    # ---------------------------------------------------------
    # UPLOAD
    # ---------------------------------------------------------
    @staticmethod
    def upload_fichier(
        db: Session,
        contenu: bytes,
        nom_original: str,
        content_type: str | None,
        user_id: int | None = None,
        ticket_id: int | None = None,
    ) -> FichierStocke:
        if (user_id is None) == (ticket_id is None):
            raise ValueError("Un fichier appartient soit à un compte, soit à un ticket, pas les deux")

        taille = len(contenu)

        if user_id is not None:
            quota_mo = StockageService.get_quota_mo(db, user_id)
        else:
            ticket = db.query(Ticket).get(ticket_id)
            if not ticket:
                raise ValueError("Ticket introuvable")
            quota_mo = QUOTA_TICKET_MO

        usage_octets = StockageService.get_usage_octets(db, user_id=user_id, ticket_id=ticket_id)
        if usage_octets + taille > quota_mo * 1024 * 1024:
            raise ValueError(f"Quota de stockage dépassé (limite : {quota_mo} Mo)")

        provider = get_provider(STORAGE_PROVIDER)
        cle = f"{user_id or ('ticket_' + str(ticket_id))}/{uuid.uuid4().hex}_{nom_original}"
        taille_ecrite = provider.upload(cle, io.BytesIO(contenu))

        fichier = FichierStocke(
            user_id=user_id,
            ticket_id=ticket_id,
            nom_original=nom_original,
            provider=STORAGE_PROVIDER,
            cle_stockage=cle,
            taille_octets=taille_ecrite,
            content_type=content_type,
        )
        db.add(fichier)
        db.commit()
        db.refresh(fichier)

        HistoriqueService.log(
            db=db,
            type_evenement="stockage_upload",
            description=f"Fichier '{nom_original}' envoyé dans l'espace de stockage",
            user_id=user_id,
            ticket_id=ticket_id,
            details={"taille_octets": taille_ecrite},
        )
        return fichier

    # ---------------------------------------------------------
    # LISTE / TÉLÉCHARGEMENT / SUPPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def lister_fichiers(db: Session, user_id: int | None = None, ticket_id: int | None = None) -> list[FichierStocke]:
        query = db.query(FichierStocke)
        if user_id is not None:
            query = query.filter(FichierStocke.user_id == user_id)
        else:
            query = query.filter(FichierStocke.ticket_id == ticket_id)
        return query.order_by(FichierStocke.date_upload.desc()).all()

    @staticmethod
    def _get_fichier_pour_proprietaire(
        db: Session, fichier_id: int, user_id: int | None, ticket_id: int | None
    ) -> FichierStocke:
        fichier = db.query(FichierStocke).get(fichier_id)
        if not fichier:
            raise ValueError("Fichier introuvable")

        if user_id is not None and fichier.user_id != user_id:
            raise ValueError("Ce fichier n'appartient pas à cet utilisateur")
        if ticket_id is not None and fichier.ticket_id != ticket_id:
            raise ValueError("Ce fichier n'appartient pas à ce ticket")

        return fichier

    @staticmethod
    def telecharger_fichier(
        db: Session, fichier_id: int, user_id: int | None = None, ticket_id: int | None = None
    ) -> tuple[FichierStocke, io.BufferedIOBase]:
        fichier = StockageService._get_fichier_pour_proprietaire(db, fichier_id, user_id, ticket_id)
        provider = get_provider(fichier.provider)
        return fichier, provider.download(fichier.cle_stockage)

    @staticmethod
    def supprimer_fichier(
        db: Session, fichier_id: int, user_id: int | None = None, ticket_id: int | None = None
    ) -> None:
        fichier = StockageService._get_fichier_pour_proprietaire(db, fichier_id, user_id, ticket_id)
        provider = get_provider(fichier.provider)
        provider.delete(fichier.cle_stockage)

        db.delete(fichier)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="stockage_delete",
            description=f"Fichier '{fichier.nom_original}' supprimé de l'espace de stockage",
            user_id=user_id,
            ticket_id=ticket_id,
        )

    # ---------------------------------------------------------
    # PURGE DU STOCKAGE TEMPORAIRE (fin de session ticket)
    # ---------------------------------------------------------
    @staticmethod
    def purger_stockage_ticket(db: Session, ticket_id: int) -> int:
        fichiers = db.query(FichierStocke).filter(FichierStocke.ticket_id == ticket_id).all()
        for fichier in fichiers:
            get_provider(fichier.provider).delete(fichier.cle_stockage)
            db.delete(fichier)
        db.commit()
        return len(fichiers)
