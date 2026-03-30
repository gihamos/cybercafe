import jwt
from params import JWT_SECRET,ALGORITHM
from datetime import datetime, timedelta
from pwdlib import PasswordHash

__password_hash=PasswordHash.recommended()


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


def get_password_hash(password):
    return __password_hash.hash(password)
