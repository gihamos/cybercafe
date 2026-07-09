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

# Origines autorisées pour le panneau d'administration web (CORS)
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Passerelle de paiement PayPal (sandbox par défaut) — voir services/payment_gateway/
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", default="")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", default="")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", default="sandbox")  # "sandbox" ou "live"
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", default="")
PAYPAL_API_BASE = (
    "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"
)
# URL du frontend vers laquelle PayPal redirige après approbation/annulation du paiement
PAYMENT_RETURN_URL = os.getenv("PAYMENT_RETURN_URL", default="http://localhost:5173/paiement/retour")
PAYMENT_CANCEL_URL = os.getenv("PAYMENT_CANCEL_URL", default="http://localhost:5173/paiement/annule")

# Stockage réseau (espace fichiers des comptes + stockage temporaire des tickets)
# Provider par défaut, voir services/storage_provider/ ("local" ou "s3")
STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", default="local")
STORAGE_LOCAL_PATH = Path(os.getenv("STORAGE_LOCAL_PATH", default=str(BASE_DIR / "data" / "stockage")))

# Provider S3/MinIO (optionnel, nécessite le paquet "boto3" — voir storage_provider/s3_provider.py)
S3_BUCKET = os.getenv("S3_BUCKET", default="")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", default="")
S3_REGION = os.getenv("S3_REGION", default="")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", default="")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", default="")

# Paiements en caisse validés par API fournisseur — voir services/in_person_gateway/
CARTE_API_BASE = os.getenv("CARTE_API_BASE", default="https://api.example-carte.com/v1")
CARTE_API_KEY = os.getenv("CARTE_API_KEY", default="")
MOBILE_MONEY_API_BASE = os.getenv("MOBILE_MONEY_API_BASE", default="https://api.example-mobilemoney.com/v1")
MOBILE_MONEY_API_KEY = os.getenv("MOBILE_MONEY_API_KEY", default="")