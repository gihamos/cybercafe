import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import logger
from router import (
    user, auth, tickets, session, poste, abonnement, article,
    paiement, bande_passante, impression, offre, notification,
    historique, system_setting, ws_poste, app_bloquee, ws_admin, paiement_en_ligne, promotion, caisse, stats,
    chat, stockage, stockage_poste, pay_connect
)
from models.user import User,UserRole
from config.database import Base,engine,SessionLocal
from params import ADMIN_DATA, CORS_ORIGINS
from utils.security import hash_password
from websocket.manager import manager


logger.info(msg="Demarage de l'application")

Base.metadata.create_all(bind=engine)

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



@app.on_event("startup")
async def on_startup():
    create_admin()
    # capture la boucle asyncio principale : permet aux endpoints REST (exécutés en
    # threadpool) de pousser des messages vers les postes connectés en WebSocket
    manager.set_loop(asyncio.get_running_loop())

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
app.include_router(stockage.router)
app.include_router(stockage_poste.router)
app.include_router(pay_connect.router)






@app.get("/")
def home():
    return {"message": "api fonctionnel"}