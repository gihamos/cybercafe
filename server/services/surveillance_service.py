import io
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.poste_screenshot import PosteScreenshot
from models.historique_navigation import HistoriqueNavigation
from models.poste import Poste
from services.storage_provider import get_provider
from services.historique_service import HistoriqueService
from params import STORAGE_PROVIDER


class SurveillanceService:

    # ---------------------------------------------------------
    # CAPTURES D'ÉCRAN
    # ---------------------------------------------------------
    @staticmethod
    def enregistrer_capture(
        db: Session, poste_id: int, contenu: bytes, content_type: str | None, session_id: int | None = None
    ) -> PosteScreenshot:
        if not db.query(Poste).get(poste_id):
            raise ValueError("Poste introuvable")

        provider = get_provider(STORAGE_PROVIDER)
        cle = f"surveillance/poste_{poste_id}/{uuid.uuid4().hex}.png"
        taille = provider.upload(cle, io.BytesIO(contenu))

        capture = PosteScreenshot(
            poste_id=poste_id,
            session_id=session_id,
            provider=STORAGE_PROVIDER,
            cle_stockage=cle,
            taille_octets=taille,
            content_type=content_type or "image/png",
        )
        db.add(capture)
        db.commit()
        db.refresh(capture)

        HistoriqueService.log(
            db=db,
            type_evenement="screenshot_capture",
            description=f"Capture d'écran du poste {poste_id}",
            poste_id=poste_id,
        )
        return capture

    @staticmethod
    def lister_captures(
        db: Session, poste_id: int | None = None, session_id: int | None = None, limit: int = 100
    ) -> list[PosteScreenshot]:
        query = db.query(PosteScreenshot)
        if poste_id is not None:
            query = query.filter(PosteScreenshot.poste_id == poste_id)
        if session_id is not None:
            query = query.filter(PosteScreenshot.session_id == session_id)
        return query.order_by(PosteScreenshot.date_capture.desc()).limit(limit).all()

    @staticmethod
    def get_capture(db: Session, capture_id: int):
        capture = db.query(PosteScreenshot).get(capture_id)
        if not capture:
            raise ValueError("Capture introuvable")
        provider = get_provider(capture.provider)
        return capture, provider.download(capture.cle_stockage)

    @staticmethod
    def supprimer_capture(db: Session, capture_id: int) -> None:
        capture = db.query(PosteScreenshot).get(capture_id)
        if not capture:
            raise ValueError("Capture introuvable")
        get_provider(capture.provider).delete(capture.cle_stockage)
        db.delete(capture)
        db.commit()

    # ---------------------------------------------------------
    # HISTORIQUE DE NAVIGATION
    # ---------------------------------------------------------
    @staticmethod
    def enregistrer_entrees(
        db: Session, poste_id: int, entrees: list[dict], session_id: int | None = None
    ) -> int:
        """Ingère une liste d'entrées {url, titre, date_visite, navigateur}. Déduplique
        silencieusement via la contrainte unique (poste_id, url, date_visite) : le client
        renvoie à chaque cycle une fenêtre glissante de son historique local, donc les
        mêmes entrées peuvent réapparaître d'un envoi à l'autre."""
        if not db.query(Poste).get(poste_id):
            raise ValueError("Poste introuvable")

        nb_inserees = 0
        for entree in entrees:
            date_visite = entree.get("date_visite")
            if isinstance(date_visite, str):
                try:
                    date_visite = datetime.fromisoformat(date_visite)
                except ValueError:
                    continue
            if not entree.get("url") or not date_visite:
                continue

            ligne = HistoriqueNavigation(
                poste_id=poste_id,
                session_id=session_id,
                url=entree["url"],
                titre=entree.get("titre"),
                navigateur=entree.get("navigateur"),
                date_visite=date_visite,
            )
            db.add(ligne)
            try:
                db.commit()
                nb_inserees += 1
            except IntegrityError:
                db.rollback()  # déjà ingérée (même poste/url/date_visite)

        if nb_inserees:
            HistoriqueService.log(
                db=db,
                type_evenement="navigation_ingestion",
                description=f"{nb_inserees} entrée(s) d'historique de navigation ingérée(s) pour le poste {poste_id}",
                poste_id=poste_id,
            )
        return nb_inserees

    @staticmethod
    def lister_historique(
        db: Session,
        poste_id: int | None = None,
        session_id: int | None = None,
        user_id: int | None = None,
        limit: int = 200,
    ) -> list[HistoriqueNavigation]:
        query = db.query(HistoriqueNavigation)
        if poste_id is not None:
            query = query.filter(HistoriqueNavigation.poste_id == poste_id)
        if session_id is not None:
            query = query.filter(HistoriqueNavigation.session_id == session_id)
        if user_id is not None:
            from models.session import Session as SessionModel
            query = query.join(SessionModel, HistoriqueNavigation.session_id == SessionModel.id).filter(
                SessionModel.user_id == user_id
            )
        return query.order_by(HistoriqueNavigation.date_visite.desc()).limit(limit).all()
