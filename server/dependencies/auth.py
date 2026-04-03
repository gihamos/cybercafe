from fastapi import HTTPException, Request,Depends
import jwt
from params import ALGORITHM, JWT_SECRET
from fastapi.security import HTTPBearer
bearer_scheme = HTTPBearer()

async def auth_dependency( request: Request, credentials = Depends(bearer_scheme)):

    try:
        # Décodage du JWT
        token=credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        request.state.user = payload
        return request

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expiré")

    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token invalide") 


