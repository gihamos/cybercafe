from fastapi import APIRouter, Depends, HTTPException
from config.database import get_db
from schemas.user import userCreate
from sqlalchemy.orm import Session
from models.user import User,UserRole
from server.dependencies.access import userRole_dependency,userAdminRole_dependency
from dependencies.auth import auth_dependency
from utils.security import get_password_hash
from typing import Union

router=APIRouter(prefix="/user",tags=["Users"],dependencies=[Depends(auth_dependency)])



@router.post("/createUser",dependencies=[Depends(userRole_dependency)])
def createUser(userModel:userCreate,db:Session=Depends(get_db)):
    userdata=userModel.model_dump()
    userdata["password"]=get_password_hash(userdata["password"])
    user=User(**userdata)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "status_code":201,
        "details":"utilisateur créé avec success",
        "data":{
            "username":user.username,
            "role": user.role
        }
    }
  
@router.post("/createManager",dependencies=[Depends(userAdminRole_dependency)])  
def createManager(userModel: userCreate,role:UserRole=UserRole.operateur,db:Session=Depends(get_db)):
    userdata=userModel.model_dump()
    userdata["password"]=get_password_hash(userdata["password"])
    userdata["role"]=role
    user=User(**userdata)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "status_code":201,
        "details":"utilisateur créé avec success",
         "data":{
            "username":user.username,
            "role":user.role
        }
        }
    
@router.get("/user/:username")
def getUser(username:str,db:Session=Depends(get_db)):
    user=db.query(User).filter(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="l'utilisateur n'existe pas")
    return {
        "status_code":200,
        "data":{
            "username":user.username,
            "email":user.email,
            "first_name":user.first_name,
            "last_name":user.last_name,
            "date_of_born":user.date_of_born,
            "solde_euros":user.solde_euros,
            "forfait":user.forfait,
            "address":user.address,
            "date_expire":user.date_expire
            
        }
    }
