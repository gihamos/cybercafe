from fastapi import APIRouter, Depends, HTTPException
from config.database import get_db
from sqlalchemy.orm import Session
from models.user import User
from utils.security import verify_password,create_access_token


router=APIRouter(prefix="/auth",tags=["auth"])


@router.post("/login")
def login(username:str,password:str,db:Session=Depends(get_db)):
    user=db.query(User).filter(username==username).first()
    if user is None or not verify_password(password,user.password):
        raise HTTPException(status_code=400,detail="username ou mot de passe incorrect")
    
    access_token={
        "username":user.username,
        "email":user.email,
        "role":user.role
    }
    token=create_access_token(access_token,120)
    return {
        "status_code":200,
        "token":token
        
    }
    