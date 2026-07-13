import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from utils.logger import logger
from router import (
    user, auth, tickets, session, poste, abonnement, article,
    paiement, bande_passante, impression, offre, notification,
    historique, system_setting, ws_poste, app_bloquee, ws_admin, paiement_en_ligne, promotion, caisse, stats,
    chat, chat_poste, stockage, stockage_poste, pay_connect, user_group, article_categorie, site_regle, config,
    surveillance, surveillance_poste, portail, reseau
)
from models.user import User,UserRole
from config.database import Base,engine,SessionLocal
from params import ADMIN_DATA, CORS_ORIGINS
from utils.security import hash_password
from websocket.manager import manager


logger.info(msg="Demarage de l'application")

Base.metadata.create_all(bind=engine)

from config.migrations import executer_migrations
executer_migrations(engine)

def create_admin():
    try:
        db=SessionLocal()
        admin = db.query(User).filter(User.role == UserRole.admin).first()

        if not admin:
            new_admin = User(
                username=ADMIN_DATA.get("username"),
                password=hash_password(ADMIN_DATA.get("password")),  #
                first_name=ADMIN_DATA.get("first_name"),
                email=ADMIN_DATA.get("email"),
                role=UserRole.admin,
                is_active=True
            )

            db.add(new_admin)
            db.commit()
            logger.info(" Admin créé avec succès")
        else:
            logger.info("Admin déjà existant")

    finally:
        db.close()


app = FastAPI(
    title="cybercafe API",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    """Un modèle Pydantic construit via Depends() (ex: UserUpdate=Depends() pour lire
    ses champs en query params, voir validators/validator.py) lève sa ValidationError
    pendant la résolution des dépendances FastAPI — hors du chemin qui convertit
    normalement une erreur de validation de corps de requête en 422, elle remonterait
    donc en 500 sans ce handler global."""
    return JSONResponse(
        status_code=422,
        content={"detail": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]},
    )



@app.on_event("startup")
async def on_startup():
    create_admin()
    # capture la boucle asyncio principale : permet aux endpoints REST (exécutés en
    # threadpool) de pousser des messages vers les postes connectés en WebSocket
    manager.set_loop(asyncio.get_running_loop())

    from config.background_tasks import demarrer_taches_de_fond
    demarrer_taches_de_fond()


@app.on_event("shutdown")
async def on_shutdown():
    from config.background_tasks import arreter_taches_de_fond
    arreter_taches_de_fond()

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(tickets.router)
app.include_router(session.router)
app.include_router(poste.router)
app.include_router(abonnement.router)
app.include_router(article.router)
app.include_router(paiement.router)
app.include_router(bande_passante.router)
app.include_router(impression.router)
app.include_router(offre.router)
app.include_router(notification.router)
app.include_router(historique.router)
app.include_router(system_setting.router)
app.include_router(ws_poste.router)
app.include_router(app_bloquee.router)
app.include_router(ws_admin.router)
app.include_router(paiement_en_ligne.router)
app.include_router(promotion.router)
app.include_router(caisse.router)
app.include_router(stats.router)
app.include_router(chat.router)
app.include_router(portail.router)
app.include_router(reseau.router)
app.include_router(chat_poste.router)
app.include_router(stockage.router)
app.include_router(stockage_poste.router)
app.include_router(pay_connect.router)
app.include_router(user_group.router)
app.include_router(article_categorie.router)
app.include_router(site_regle.router)
app.include_router(config.router)
app.include_router(surveillance.router)
app.include_router(surveillance_poste.router)






@app.get("/")
def home():
    return {"message": "api fonctionnel"}