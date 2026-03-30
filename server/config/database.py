from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from params import DATABASEURL
from utils.logger import logger


engine = create_engine(
    DATABASEURL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()