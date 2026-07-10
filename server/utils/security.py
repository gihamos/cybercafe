import jwt
import secrets
from params import JWT_SECRET,ALGORITHM
from datetime import datetime, timedelta
from pwdlib import PasswordHash

__password_hash=PasswordHash.recommended()

# Alphabet sans caractères ambigus (0/O, 1/l/I) — un mot de passe provisoire doit être
# lisible et dictable à l'oral/par téléphone par un opérateur à un client.
_TEMP_PASSWORD_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"


def generate_temp_password(length: int = 10) -> str:
    return ''.join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length))


def create_access_token(data: dict, expire:int=60):
    to_encode = data.copy() 
    expire = datetime.now() + timedelta(minutes=expire) 
    to_encode.update({"exp": expire}) 
    return jwt.encode(to_encode,JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    payload = data.copy()
    payload["type"] = "refresh"
    payload["exp"] = datetime.now() + timedelta(minutes=60)
    return jwt.encode(payload,JWT_SECRET, algorithm=ALGORITHM)

def verify_password(plain_password, hashed_password)-> bool:
    return __password_hash.verify(plain_password, hashed_password)


def hash_password(password):
    return __password_hash.hash(password)
