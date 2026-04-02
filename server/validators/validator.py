from fastapi import HTTPException,Depends
from schemas.user_schema import UserFilter, BaseModel

def validate_user_filter(filters: UserFilter = Depends()):
    data = filters.model_dump()

    if not any(value is not None for value in data.values()):
        raise HTTPException(
            status_code=400,
            detail="Au moins un filtre doit être fourni"
        )

    return filters

def validate_not_empty_data(model:BaseModel=Depends()):
     data = model.model_dump()
    
     if not any(value is not None for value in data.values()):
        raise HTTPException(
         status_code=400,
         detail="Au moins un champs doit être fourni"
     )
     return model