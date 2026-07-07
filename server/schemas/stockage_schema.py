from pydantic import BaseModel


class QuotaUpdate(BaseModel):
    quota_stockage_mo: float | None = None
