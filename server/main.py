from fastapi import FastAPI
from utils.logger import logger


app = FastAPI(
    title="cybercafe API",
    version="1.0",
)


logger.info(msg="Demarage de l'application")




@app.get("/")
def home():
    return {"message": "api fonctionnel"}