from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from config.database import get_db
from sqlalchemy.orm import Session
from models.user import UserRole, User
from dependencies.access import require_roles,user_access_dependency,get_current_user
from dependencies.auth import auth_dependency
from services.user_service import UserService
from services.permission_service import PermissionService, PERMISSIONS_TOUTES
from schemas.user_schema import UserCreate,UserResponse,UserFilter,UserUpdate,PermissionsUpdate
from validators.validator import validate_user_filter,validate_not_empty_data
from datetime import datetime

router=APIRouter(prefix="/user",tags=["Users"],dependencies=[Depends(auth_dependency)])



@router.post("/createClient",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def createClient(userModel:UserCreate,db:Session=Depends(get_db)):
    try:
        # comment: 
        userModel.role=UserRole.client
        data=userModel.model_dump(exclude_unset=True)
        user =UserService.create_user(db,data)
        return UserResponse(id=user.id,
                            username=user.username,
                            email=user.email,
                            solde_euros=user.solde_euros,
                            is_active=user.is_active,
                            date_create=user.date_create,
                            date_expire=user.date_expire or None,
                            piece_identite_type=user.piece_identite_type,
                            piece_identite_numero=user.piece_identite_numero,
                            piece_identite_organisme=user.piece_identite_organisme,
                            piece_identite_expiration=user.piece_identite_expiration,
                            a_une_piece_identite=user.piece_identite_cle_stockage is not None,
                            a_une_photo=user.photo_profil_cle_stockage is not None,
                            notes=user.notes,
                            groupe_ids=[g.id for g in user.groupes])
    except Exception as e:
        raise HTTPException(status_code=400,detail={
            "error":True,
            "message":str(e)
        })
    # end try
    
    
    
    
    
  
@router.post("/createUser",
             dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))],
             response_model=UserResponse,
             response_model_exclude_none=True,
             response_model_exclude_unset=True)  
def createManager(data: UserCreate,db:Session=Depends(get_db)):
    try:
     # comment: 
        data_load=data.model_dump(exclude_unset=True)
        user =UserService.create_user(db,data_load)
        return user
    except Exception as e:
        raise HTTPException(status_code=400,detail={
         "error":True,
         "message":str(e)
        })
 # end try
        
    
    
@router.get("/clients",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def get_all_clients(db:Session=Depends(get_db)):
    
    try:
        # comment: 
        users=UserService.getuser(db=db,filters={"role":UserRole.client,"limit":50})
 
        usersdata=[{
        "id":user.id,
        "username":user.username,
        "email":user.email,
        "first_name":user.first_name,
        "last_name":user.last_name,
        "date_of_born":user.date_of_born,
        "solde_euros":user.solde_euros,
        "abonnement_courant":user.current_abonnement or None,
        "offres_acheter":user.achat_offres or None,
        "address":user.address,
        "date_create":user.date_create,
        "date_expire":user.date_expire,
        "is_active":user.is_active,
        "piece_identite_type":user.piece_identite_type,
        "piece_identite_numero":user.piece_identite_numero,
        "piece_identite_organisme":user.piece_identite_organisme,
        "piece_identite_expiration":user.piece_identite_expiration,
        "a_une_piece_identite":user.piece_identite_cle_stockage is not None,
        "a_une_photo":user.photo_profil_cle_stockage is not None,
        "notes":user.notes,
        "groupe_ids":[g.id for g in user.groupes],
        "groupe_noms":[g.nom for g in user.groupes],
        } for user in users]
 
        return {
        "status_code":200,
        "data":usersdata
         }
    except Exception as e:
        raise HTTPException(status_code=400,detail={
        "error":True,
        "message":str(e)
        })
        
    # end try
    
    

@router.get("/query/clients",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def get_clients(
    filters: UserFilter = Depends(validate_user_filter),
    db: Session = Depends(get_db)
):
   try:
     # comment:
     filters_dict=filters.model_dump()
     filters_dict["role"]=UserRole.client
     users=UserService.getuser(db=db,filters=filters_dict)
     usersdata=[{
     "id":user.id,
     "username":user.username,
     "email":user.email,
     "first_name":user.first_name,
     "last_name":user.last_name,
     "date_of_born":user.date_of_born,
     "solde_euros":user.solde_euros,
     "abonnement_courant":user.current_abonnement or None,
     "offres_acheter":user.achat_offres or None,
     "address":user.address,
     "date_create":user.date_create,
     "date_expire":user.date_expire,
     "is_active":user.is_active,
     "piece_identite_type":user.piece_identite_type,
     "piece_identite_numero":user.piece_identite_numero,
     "piece_identite_organisme":user.piece_identite_organisme,
     "piece_identite_expiration":user.piece_identite_expiration,
     "a_une_piece_identite":user.piece_identite_cle_stockage is not None,
     "a_une_photo":user.photo_profil_cle_stockage is not None,
     "notes":user.notes,
     "groupe_ids":[g.id for g in user.groupes],
     "groupe_noms":[g.nom for g in user.groupes],
     } for user in users]
     return {
     "status_code":200,
     "data":usersdata
      }
   except Exception as e:
     raise HTTPException(status_code=400,detail={
     "error":True,
     "message":str(e)
     })

 # end try
 

@router.get("/equipe",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def get_equipe(db: Session = Depends(get_db)):
    try:
        users = UserService.getuser(db=db, filters={"role_in": [UserRole.admin, UserRole.operateur], "limit": 100})
        usersdata = [{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "date_create": user.date_create,
            "permissions": user.permissions,
        } for user in users]
        return {"status_code": 200, "data": usersdata}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": True, "message": str(e)})


@router.get("/permissions/catalogue", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def get_permissions_catalogue():
    return {"status_code": 200, "data": PERMISSIONS_TOUTES}


@router.get("/me/permissions")
def get_mes_permissions(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    permissions = PermissionService.get_permissions_effectives(db=db, user_id=currentuser["id"])
    return {"status_code": 200, "data": {"role": currentuser["role"], "permissions": permissions}}


@router.get("/{username}/permissions", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def get_permissions_operateur(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"status_code": 200, "data": {"permissions": user.permissions}}


@router.patch("/{username}/permissions", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def set_permissions_operateur(username: str, data: PermissionsUpdate, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    try:
        user = PermissionService.set_permissions(db=db, user_id=user.id, permissions=data.permissions, operateur_id=currentuser["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": {"permissions": user.permissions}}


@router.patch("/setupdateUser/{username}",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin,UserRole.operateur]))])
def setUpdateCompte(
    username: str,
    active:bool=None,
    exipredate:datetime=None,
    currentuser=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # comment: 
        user=UserService.setUpdateCompte(user_iden=username,currentuser=currentuser,exipredate=exipredate,db=db,active=active)
        return {
        "status_code":200,
        "data": {
        "username": user.username,
        "date_expire": user.date_expire or None,
        "active":user.is_active
        }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
    # end try
    

@router.patch("/updateRole/{username}",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])    
def updateRole(username:str, role:UserRole=UserRole.operateur,db: Session = Depends(get_db)):
    try:
        # comment: 
        user=UserService.update_role(db=db,user_iden=username,role=role)
        return {
        "status_code":200,
        "data": {
        "username": user.username,
        "date_expire": user.date_expire,
        "role":user.role
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
    
     
      
 
@router.delete("/{username}",dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])    
def deleteUser(username:str,db: Session = Depends(get_db)): 
    try:
        # comment: 
        sup=UserService.delete_user(user_iden=username)
        return {
            "status_code":200,
            "data": 1 if sup else 0
        }
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
    # end try
    
    
    
@router.get("/{username}",dependencies=[Depends(user_access_dependency())])
def getUser(username:str,db:Session=Depends(get_db)):
  try:
     # comment: 
     users=UserService.getuser(db=db,filters={"username":username})
     usersdata=[{
     "username":user.username,
     "email":user.email,
     "first_name":user.first_name,
     "last_name":user.last_name,
     "date_of_born":user.date_of_born,
     "solde_euros":user.solde_euros,
     "abonnement_courant":user.current_abonnement or None,
     "offres_acheter":user.achat_offres or None,
     "address":user.address,
     "date_create":user.date_create,
     "date_expire":user.date_expire,
     "is_active":user.is_active,
     "piece_identite_type":user.piece_identite_type,
     "piece_identite_numero":user.piece_identite_numero,
     "piece_identite_organisme":user.piece_identite_organisme,
     "piece_identite_expiration":user.piece_identite_expiration,
     "a_une_piece_identite":user.piece_identite_cle_stockage is not None,
     "a_une_photo":user.photo_profil_cle_stockage is not None,
     "notes":user.notes,
     } for user in users]
     return {
     "status_code":200,
     "data":usersdata
      }
  except Exception as e:
     raise HTTPException(status_code=400,detail={
     "error":True,
     "message":str(e)
     })
    
        
@router.patch("/{username}",dependencies=[Depends(user_access_dependency())])
def update_user(username:str,user_update:UserUpdate= Depends(validate_not_empty_data),db:Session=Depends(get_db)):
    try:
        # comment:
        user=UserService.update_user(db=db,user_iden=username,data=user_update)
        return {
            "status_code":200,
            "data":{
                "username":user.username,
                "champs_modifie":user_update.model_dump(exclude_unset=True)
            },
            "message":"mise à jour fait avec succès"
        }
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
    # end try


@router.post("/{username}/reset-password", dependencies=[Depends(user_access_dependency())])
def reset_password(username: str, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Génère un nouveau mot de passe provisoire pour ce compte (perte de mot de passe) —
    renvoyé UNE SEULE FOIS en clair ici, jamais stocké ni journalisé en clair : à l'appelant
    (opérateur/admin) de le communiquer au client."""
    try:
        mot_de_passe_provisoire = UserService.reset_password(db=db, user_iden=username, operateur_id=currentuser.get("id"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": {"username": username, "mot_de_passe_provisoire": mot_de_passe_provisoire}}


def _resoudre_user_id(db: Session, username: str) -> int:
    cible = db.query(User).filter(User.username == username).first()
    if not cible:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return cible.id


@router.post("/{username}/photo", dependencies=[Depends(user_access_dependency())])
async def uploader_photo(username: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    contenu = await file.read()
    try:
        UserService.set_photo(db=db, user_id=_resoudre_user_id(db, username), contenu=contenu, content_type=file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status_code": 200, "data": 1}


@router.get("/{username}/photo", dependencies=[Depends(user_access_dependency())])
def telecharger_photo(username: str, db: Session = Depends(get_db)):
    try:
        user, flux = UserService.get_photo(db=db, user_id=_resoudre_user_id(db, username))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StreamingResponse(flux, media_type=user.photo_profil_content_type or "application/octet-stream")


@router.delete("/{username}/photo", dependencies=[Depends(user_access_dependency())])
def supprimer_photo(username: str, db: Session = Depends(get_db)):
    try:
        UserService.supprimer_photo(db=db, user_id=_resoudre_user_id(db, username))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status_code": 200, "data": 1}


@router.post("/{username}/piece-identite/fichier", dependencies=[Depends(user_access_dependency())])
async def uploader_piece_identite(username: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    contenu = await file.read()
    try:
        UserService.set_piece_identite_fichier(db=db, user_id=_resoudre_user_id(db, username), contenu=contenu, content_type=file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status_code": 200, "data": 1}


@router.get("/{username}/piece-identite/fichier", dependencies=[Depends(user_access_dependency())])
def telecharger_piece_identite(username: str, db: Session = Depends(get_db)):
    try:
        user, flux = UserService.get_piece_identite_fichier(db=db, user_id=_resoudre_user_id(db, username))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StreamingResponse(flux, media_type=user.piece_identite_content_type or "application/octet-stream")


@router.delete("/{username}/piece-identite/fichier", dependencies=[Depends(user_access_dependency())])
def supprimer_piece_identite(username: str, db: Session = Depends(get_db)):
    try:
        UserService.supprimer_piece_identite_fichier(db=db, user_id=_resoudre_user_id(db, username))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status_code": 200, "data": 1}


