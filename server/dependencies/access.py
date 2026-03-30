from fastapi import HTTPException, Request
from models.user import UserRole


async def userRole_dependency(request: Request, role: list[UserRole]=[UserRole.admin,UserRole.operateur]):
    if not getattr(request.state, 'user', None):
        raise HTTPException(status_code=401, detail="utilisateur non authentifié")
    print("\ndata request: ",request.state.user,"\n")
    user_data = request.state.user
    
    if "role" not in user_data: 
        raise HTTPException(status_code=400, detail="Rôle manquant dans le token")


    local_role = UserRole(user_data["role"])


    if local_role not in role:
        raise HTTPException(status_code=403, detail="vous n'avez pas les droits de faire cette opération")
    
    
async def userAdminRole_dependency(request: Request):
    if not getattr(request.state, 'user', None):
        raise HTTPException(status_code=401, detail="utilisateur non authentifié")
    print("\ndata request: ",request.state.user,"\n")
    user_data = request.state.user
    
    if "role" not in user_data: 
        raise HTTPException(status_code=400, detail="Rôle manquant dans le token")




    local_role = UserRole(user_data["role"])




    if local_role !=UserRole.admin:
        raise HTTPException(status_code=403, detail="vous n'avez pas les droits de faire cette opération")
    
    
async def userAccess_dependency(request: Request,username:str):
    if not getattr(request.state, 'user', None):
        raise HTTPException(status_code=401, detail="utilisateur non authentifié")

    user_data = request.state.user
    

    if "role" not in user_data: 
        raise HTTPException(status_code=400, detail="Rôle manquant dans le token")
    local_role = UserRole(user_data["role"])
    if (local_role not in [UserRole.admin,UserRole.operateur]) or (username!=getattr(user_data,"username",None)):
        raise HTTPException(status_code=403, detail="vous n'avez pas les droits de faire cette opération")
    