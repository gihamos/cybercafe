from fastapi import APIRouter, Depends, HTTPException,Request
from config.database import get_db
from sqlalchemy.orm import Session
from models.user import User
from utils.security import verify_password,create_access_token
from services.user_service import UserService
from utils.logger import logger
from dependencies.auth import auth_dependency


router=APIRouter(prefix="/auth",tags=["auth"])


@router.post("/login")
def login(username:str,password:str,db:Session=Depends(get_db)):
    try:
    # comment: 
        user=UserService.authenticate(db=db,username=username,password=password)
    
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
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400,detail=e)
  

@router.get("/refreshToken")
def refreshToken(req:Request=Depends(auth_dependency)) :
    access_token={
     "username":req.state.user.get("username"),
     "email":req.state.user.get("email"),
     "role":req.state.user.get("role")
     }
    token=create_access_token(access_token,120)
    return {
     "status_code":200,
     "token":token
        }
    