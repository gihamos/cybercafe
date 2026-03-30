import os
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


DATABASEPATH=Path(BASE_DIR / "data")
DATABASEPATH.mkdir(exist_ok=True)
DATABASEURL=os.getenv("DATABASE_URL",default=f"sqlite:///{DATABASEPATH}/cybercafe.db")


JWT_SECRET=os.getenv("JWT_SECRET", "12c772d5f202e6e965733a956e0a32f5c12c3d500452844cb63d50c1aa478090")
ALGORITHM = "HS256"

ADMIN_DATA={
    "username":os.getenv("ADMINUSERNAME",default="admin123"),
    "password": os.getenv("ADMINPASSWORD",default="admin123"),
    "email":os.getenv("ADMINEMAIL",default="admin123@cybercafe.com"),
    "first_name":os.getenv("ADMINFIRSTNAME",default="admin")
}