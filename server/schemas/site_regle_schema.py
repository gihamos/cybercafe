from pydantic import BaseModel
from typing import Optional


class SiteRegleCreate(BaseModel):
    domaine: str
    groupe_id: Optional[int] = None
    description: Optional[str] = None
    age_min: Optional[int] = None


class SiteRegleUpdate(BaseModel):
    domaine: Optional[str] = None
    description: Optional[str] = None
    actif: Optional[bool] = None
    age_min: Optional[int] = None
