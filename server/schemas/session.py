from pydantic import BaseModel
from typing import Optional

class Session_start(BaseModel):
    username:Optional[str]=None
    code:Optional[str]=None
    poste_id:Optional[str]=None