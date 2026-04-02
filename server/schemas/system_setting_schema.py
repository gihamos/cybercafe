from pydantic import BaseModel
from typing import Any, Optional


class SystemSettingBase(BaseModel):
    cle: str
    categorie: str
    valeur: Any
    description: Optional[str] = None


class SystemSettingCreate(SystemSettingBase):
    pass


class SystemSettingUpdate(BaseModel):
    valeur: Any
    description: Optional[str] = None


class SystemSettingResponse(SystemSettingBase):
    id: int
    date_modification: str

    class Config:
        orm_mode = True
