from pydantic import BaseModel,EmailStr
from typing import Optional

from enum import Enum
from datetime import date,datetime

class userCreate(BaseModel):
    username : str
    password :str
    first_name :str
    last_name :Optional[str]
    email:EmailStr
    date_of_born:date
    is_active :bool=False
    address = Optional[str]
    date_expire = Optional[datetime]

class userUpdate(BaseModel):
    password :Optional[str]
    first_name :Optional[str]
    last_name :Optional[str]
    email:Optional[EmailStr]
    date_of_born:date
    address = Optional[str]