from fastapi import FastAPI
from utils.logger import logger
from router import user,auth,tickets
from models.user import User,UserRole
from config.database import Base,engine,SessionLocal
from params import ADMIN_DATA
from utils.security import hash_password


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



@app.on_event("startup")
def on_startup():
    create_admin()
    
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(tickets.router)






@app.get("/")
def home():
    return {"message": "api fonctionnel"}