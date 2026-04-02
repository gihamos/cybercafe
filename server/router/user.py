from fastapi import APIRouter, Depends, HTTPException
from config.database import get_db
from sqlalchemy.orm import Session
from models.user import User,UserRole
from dependencies.access import require_roles,user_access_dependency,get_current_user
from dependencies.auth import auth_dependency
from utils.security import get_password_hash
from validators.validator import validate_user_filter
from datetime import datetime

router=APIRouter(prefix="/user",tags=["Users"],dependencies=[Depends(auth_dependency)])



@router.post("/createUser",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def createUser(userModel:UserCreate,db:Session=Depends(get_db)):
    userdata=userModel.model_dump(exclude_unset=True)
    user=db.query(User).filter(User.username==userdata["username"] or User.email==userdata["email"]).first()
    
    if user is not None:
        raise HTTPException(status_code=404, detail="ce username ou cet email est déjà utilisé")
        
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
  
@router.post("/createManager",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])  
def createManager(userModel: UserCreate,role:UserRole=UserRole.operateur,db:Session=Depends(get_db)):
    userdata=userModel.model_dump(exclude_unset=True)
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
    
    
@router.get("/clients",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def get_all_clients(db:Session=Depends(get_db)):
    print("\ntest daccc\n")
    users=db.query(User).filter(User.role==UserRole.client).all()
    print("\ntest daccc\n")
    usersdata=[{
        "username":user.username,
        "email":user.email,
        "first_name":user.first_name,
        "last_name":user.last_name,
        "date_of_born":user.date_of_born,
        "solde_euros":user.solde_euros,
        "forfait":user.forfait,
        "address":user.address,
        "date_create":user.date_create,
        "date_expire":user.date_expire
        } for user in users]
    
    return {
    "status_code":200,
     "data":usersdata
    }
    
    

@router.get("/query/clients",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def get_clients(
    filters: UserFilter = Depends(validate_user_filter),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role == UserRole.client)

    # filtres
    if filters.username:
        query = query.filter(User.username.contains(filters.username))

    if filters.email:
        query = query.filter(User.email.contains(filters.email))

    if filters.first_name:
        query = query.filter(User.first_name.contains(filters.first_name))

    if filters.is_active is not None:
        query = query.filter(User.is_active == filters.is_active)

    if filters.min_solde is not None:
        query = query.filter(User.solde_euros >= filters.min_solde)

    if filters.max_solde is not None:
        query = query.filter(User.solde_euros <= filters.max_solde)

    if filters.date_created_after:
        query = query.filter(User.date_create >= filters.date_created_after)

    if filters.date_created_before:
        query = query.filter(User.date_create <= filters.date_created_before)

    # tri sécurisé
    if filters.sort_by:
        field = SORT_FIELDS.get(filters.sort_by)

        if not field:
            raise HTTPException(status_code=400, detail="Champ de tri invalide")

        query = query.order_by(field)

    # pagination
    query = query.offset(filters.offset).limit(filters.limit)

    users = query.all()

    return {
        "count": len(users),
        "limit": filters.limit,
        "offset": filters.offset,
        "data": users
    }
    

@router.patch("/setupdateUser/{username}",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def setUpdateCompte(
    username: str,
    active:bool=None,
    exipredate:datetime=None,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    if active is None and exipredate is None:
        raise HTTPException(
            status_code=400,
            detail="Il faut au moins active ou exipredate"
        )

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    if (UserRole(currentuser.role)==UserRole.operateur) and (UserRole(user.role)==UserRole.operateur or UserRole(user.role)==UserRole.admin):
        raise HTTPException(status_code=400,detail=f" vous avez pas le droit de faire cet opération sur l'utlisateur : {user.username} ")

    # update
    if active is not None:
        user.is_active = active

    if exipredate is not None:
        
        if exipredate <user.date_create:
            raise HTTPException(status_code=400,detail=" la date d'expiration doit être superieur à la date de creation")
            
        user.date_expire = exipredate

    db.commit()
    db.refresh(user)

    return {
 "status_code":200,
  "data": {
      "username": user.username,
      "date_expire": user.date_expire,
      "active":user.is_active
  }
 }
    
@router.patch("/updateRole/{username}",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])    
def updateRole(username:str, role:UserRole=UserRole.operateur,db: Session = Depends(get_db)):
     user = db.query(User).filter(User.username == username).first()
     if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
     user.role=role
     db.commit()
     db.refresh(user)
     
     return {
        "status_code":200,
        "data": {
            "username": user.username,
            "date_expire": user.date_expire,
            "role":user.role
                }
            }
    
 
@router.delete("/{username}",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])    
def deleteUser(username:str,db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")  
    
    db.delete(user)
    db.commit()
    
    return {
        "status_code":200,
        "username":user.username
    }
    
    
    
@router.get("/{username}",dependencies=[Depends(user_access_dependency())])
def getUser(username:str,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.username==username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="l'utilisateur n'existe pas ggg")
    return {
        "status_code":200,
        "data":{
            "username":user.username,
            "email":user.email,
            "first_name":user.first_name,
            "last_name":user.last_name,
            "date_of_born":user.date_of_born,
            "role":user.role,
            "solde_euros":user.solde_euros,
            "forfait":user.forfait,
            "address":user.address,
            "date_create":user.date_create,
            "date_expire":user.date_expire
            
        }
    }
    
    
    
        
@router.patch("/{username}",dependencies=[Depends(user_access_dependency)])
def update_user(username:str,user_update:UserUpdate,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.username==username).first()
    if user is None:
     raise HTTPException(status_code=404, detail="l'utilisateur n'existe pas")
    update_data=user_update.model_dump(exclude_unset=True)
    
    if "email" in update_data.keys() and db.query(User).filter(User.email==update_data["email"]).first() is not None:
         raise HTTPException(status_code=404, detail="ce mail n'existe déjà")
     
    if "password" in update_data.keys():
        update_data["password"]=get_password_hash(update_data["password"])
        
        
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
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
         "date_create":user.date_create,
         "date_expire":user.date_expire
         
        }
    }