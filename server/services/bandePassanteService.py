from sqlalchemy.orm import Session
from datetime import datetime

from models.bandePassante import (
    BandePassanteProfil,
    BandePassanteUsage,
    TypeProfilBP
)
from services.notificationService import NotificationService
from services.historiqueService import HistoriqueService
from models.notification import TypeNotification


class BandePassanteService:

    # ---------------------------------------------------------
    # 1. CRÉER OU METTRE À JOUR UN PROFIL
    # ---------------------------------------------------------
    @staticmethod
    def definir_profil(
        db: Session,
        type_profil: TypeProfilBP,
        download_mbps: float | None = None,
        upload_mbps: float | None = None,
        quota_journalier_mo: float | None = None,
        quota_mensuel_mo: float | None = None,
        bloquer_si_depasse: bool = False,
        offre_id: int | None = None,
        abonnement_id: int | None = None,
        ticket_id: int | None = None,
        user_id: int | None = None,
        poste_id: int | None = None
    ):
        # Vérifier si un profil existe déjà
        profil = (
            db.query(BandePassanteProfil)
            .filter(BandePassanteProfil.type_profil == type_profil)
            .filter(BandePassanteProfil.offre_id == offre_id)
            .filter(BandePassanteProfil.abonnement_id == abonnement_id)
            .filter(BandePassanteProfil.ticket_id == ticket_id)
            .filter(BandePassanteProfil.user_id == user_id)
            .filter(BandePassanteProfil.poste_id == poste_id)
            .first()
        )

        if not profil:
            profil = BandePassanteProfil(
                type_profil=type_profil,
                offre_id=offre_id,
                abonnement_id=abonnement_id,
                ticket_id=ticket_id,
                user_id=user_id,
                poste_id=poste_id
            )
            db.add(profil)

        profil.download_mbps = download_mbps
        profil.upload_mbps = upload_mbps
        profil.quota_journalier_mo = quota_journalier_mo
        profil.quota_mensuel_mo = quota_mensuel_mo
        profil.bloquer_si_depasse = bloquer_si_depasse

        db.commit()
        db.refresh(profil)

        HistoriqueService.log(
            db=db,
            type_evenement="bp_profil_update",
            description=f"Profil BP mis à jour ({type_profil})",
            details={
                "download": download_mbps,
                "upload": upload_mbps,
                "quota_journalier": quota_journalier_mo,
                "quota_mensuel": quota_mensuel_mo
            }
        )

        return profil

    # ---------------------------------------------------------
    # 2. RÉCUPÉRER LE PROFIL APPLICABLE (priorité intelligente)
    # ---------------------------------------------------------
    @staticmethod
    def get_profil_applicable(
        db: Session,
        user_id: int | None = None,
        ticket_id: int | None = None,
        poste_id: int | None = None,
        abonnement_id: int | None = None,
        offre_id: int | None = None
    ):
        """
        Priorité :
        1. User
        2. Ticket
        3. Poste
        4. Abonnement
        5. Offre
        """

        if user_id:
            profil = db.query(BandePassanteProfil).filter_by(
                type_profil=TypeProfilBP.USER, user_id=user_id
            ).first()
            if profil:
                return profil

        if ticket_id:
            profil = db.query(BandePassanteProfil).filter_by(
                type_profil=TypeProfilBP.TICKET, ticket_id=ticket_id
            ).first()
            if profil:
                return profil

        if poste_id:
            profil = db.query(BandePassanteProfil).filter_by(
                type_profil=TypeProfilBP.POSTE, poste_id=poste_id
            ).first()
            if profil:
                return profil

        if abonnement_id:
            profil = db.query(BandePassanteProfil).filter_by(
                type_profil=TypeProfilBP.ABONNEMENT, abonnement_id=abonnement_id
            ).first()
            if profil:
                return profil

        if offre_id:
            profil = db.query(BandePassanteProfil).filter_by(
                type_profil=TypeProfilBP.OFFRE, offre_id=offre_id
            ).first()
            if profil:
                return profil

        return None

    # ---------------------------------------------------------
    # 3. ENREGISTRER LA CONSOMMATION
    # ---------------------------------------------------------
    @staticmethod
    def enregistrer_usage(
        db: Session,
        session_id: int | None,
        user_id: int | None,
        ticket_id: int | None,
        download_mo: float,
        upload_mo: float
    ):
        usage = BandePassanteUsage(
            session_id=session_id,
            user_id=user_id,
            ticket_id=ticket_id,
            data_download_mo=download_mo,
            data_upload_mo=upload_mo,
            data_total_mo=download_mo + upload_mo,
            date_enregistrement=datetime.utcnow()
        )

        db.add(usage)
        db.commit()

        return usage

    # ---------------------------------------------------------
    # 4. CALCULER LA CONSOMMATION JOURNALIÈRE / MENSUELLE
    # ---------------------------------------------------------
    @staticmethod
    def get_consommation(db: Session, user_id=None, ticket_id=None):
        query = db.query(BandePassanteUsage)

        if user_id:
            query = query.filter(BandePassanteUsage.user_id == user_id)

        if ticket_id:
            query = query.filter(BandePassanteUsage.ticket_id == ticket_id)

        usages = query.all()

        total = sum(u.data_total_mo for u in usages)
        download = sum(u.data_download_mo for u in usages)
        upload = sum(u.data_upload_mo for u in usages)

        return {
            "total_mo": total,
            "download_mo": download,
            "upload_mo": upload
        }

    # ---------------------------------------------------------
    # 5. VÉRIFIER LES QUOTAS ET BLOQUER SI NÉCESSAIRE
    # ---------------------------------------------------------
    @staticmethod
    def verifier_quota(db: Session, profil: BandePassanteProfil, user_id=None, ticket_id=None):
        consommation = BandePassanteService.get_consommation(db, user_id, ticket_id)

        # Quota journalier
        if profil.quota_journalier_mo and consommation["total_mo"] >= profil.quota_journalier_mo:
            if profil.bloquer_si_depasse:
                return "quota_journalier_depasse"

        # Quota mensuel
        if profil.quota_mensuel_mo and consommation["total_mo"] >= profil.quota_mensuel_mo:
            if profil.bloquer_si_depasse:
                return "quota_mensuel_depasse"

        return "ok"

    # ---------------------------------------------------------
    # 6. BLOQUER UN USER / TICKET SI QUOTA DÉPASSÉ
    # ---------------------------------------------------------
    @staticmethod
    def appliquer_blocage(db: Session, profil: BandePassanteProfil, user_id=None, ticket_id=None):
        statut = BandePassanteService.verifier_quota(db, profil, user_id, ticket_id)

        if statut == "ok":
            return False

        # Notification
        if user_id:
            NotificationService.send_to_user(
                db=db,
                user_id=user_id,
                titre="Quota dépassé",
                message="Votre quota de bande passante a été dépassé.",
                type_notification=TypeNotification.BANDE_PASSANTE
            )

        HistoriqueService.log(
            db=db,
            type_evenement="bp_blocage",
            description=f"Blocage bande passante ({statut})",
            user_id=user_id,
            ticket_id=ticket_id
        )

        return True

    # ---------------------------------------------------------
    # 7. RÉCUPÉRER LES USAGES
    # ---------------------------------------------------------
    @staticmethod
    def get_usages(db: Session, user_id=None, ticket_id=None, session_id=None):
        query = db.query(BandePassanteUsage)

        if user_id:
            query = query.filter(BandePassanteUsage.user_id == user_id)

        if ticket_id:
            query = query.filter(BandePassanteUsage.ticket_id == ticket_id)

        if session_id:
            query = query.filter(BandePassanteUsage.session_id == session_id)

        return query.order_by(BandePassanteUsage.date_enregistrement.desc()).all()
