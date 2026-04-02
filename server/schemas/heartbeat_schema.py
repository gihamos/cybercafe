from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
class HeartbeatBase(BaseModel):
    poste_id: int
    est_en_ligne: bool = True
    ip: Optional[str] = None
    mac_adresse: Optional[str] = None

    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    upload_mbps: Optional[float] = None
    download_mbps: Optional[float] = None

    version_client: Optional[str] = None
    uptime_seconds: Optional[int] = None

    erreurs: Optional[Dict[str, Any]] = None
    commande_en_attente: Optional[str] = None
    commande_details: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------
# CRÉATION
# ---------------------------------------------------------
class HeartbeatCreate(HeartbeatBase):
    pass


# ---------------------------------------------------------
# MISE À JOUR
# ---------------------------------------------------------
class HeartbeatUpdate(BaseModel):
    est_en_ligne: Optional[bool] = None
    ip: Optional[str] = None
    mac_adresse: Optional[str] = None

    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    upload_mbps: Optional[float] = None
    download_mbps: Optional[float] = None

    version_client: Optional[str] = None
    uptime_seconds: Optional[int] = None

    erreurs: Optional[Dict[str, Any]] = None
    commande_en_attente: Optional[str] = None
    commande_details: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------
# RÉPONSE API
# ---------------------------------------------------------
class HeartbeatResponse(HeartbeatBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
