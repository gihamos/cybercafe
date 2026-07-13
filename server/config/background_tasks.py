import asyncio

from config.database import SessionLocal
from utils.logger import logger


async def _boucle_impression(intervalle: int):
    """Fait avancer les demandes d'impression réglées vers la vraie imprimante
    (voir services/impression_service.py::traiter_file_attente/verifier_jobs_en_cours),
    et interroge le statut des jobs déjà envoyés."""
    from services.impression_service import ImpressionService

    while True:
        await asyncio.sleep(intervalle)
        db = SessionLocal()
        try:
            await asyncio.to_thread(ImpressionService.traiter_file_attente, db)
            await asyncio.to_thread(ImpressionService.verifier_jobs_en_cours, db)
        except Exception as e:
            logger.error(f"Erreur dans la boucle du serveur d'impression : {e}")
        finally:
            db.close()


async def _boucle_expiration_sessions(intervalle: int):
    """Ferme les sessions dont le temps/quota est épuisé — déclenche au passage la
    révocation réseau réelle (voir services/session_service.py::fermer_session et
    services/reseau_service.py), condition nécessaire pour qu'une session qui expire
    sans action du client coupe effectivement son accès internet."""
    from services.session_service import SessionService

    while True:
        await asyncio.sleep(intervalle)
        db = SessionLocal()
        try:
            await asyncio.to_thread(SessionService.verifier_expirations, db)
        except Exception as e:
            logger.error(f"Erreur dans la boucle de vérification des sessions : {e}")
        finally:
            db.close()


_TACHES: list[asyncio.Task] = []


def demarrer_taches_de_fond():
    from params import PRINT_WORKER_INTERVAL_SECONDS

    _TACHES.append(asyncio.create_task(_boucle_impression(PRINT_WORKER_INTERVAL_SECONDS)))
    _TACHES.append(asyncio.create_task(_boucle_expiration_sessions(30)))
    logger.info("Tâches de fond démarrées (serveur d'impression, expiration des sessions)")


def arreter_taches_de_fond():
    for tache in _TACHES:
        tache.cancel()
    _TACHES.clear()
