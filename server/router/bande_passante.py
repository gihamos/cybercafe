from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.bande_passante import BandePassanteProfil, BandePassanteUsage
from schemas.bande_passante_schema import BandePassanteProfilCreate
from services.bande_passante_service import BandePassanteService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles


router = APIRouter(
    prefix="/bande-passante",
    tags=["bande passante"],
    dependencies=[Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))]
)


def _serialize_profil(profil: BandePassanteProfil) -> dict:
    return {
        "id": profil.id,
        "type_profil": profil.type_profil,
        "offre_id": profil.offre_id,
        "abonnement_id": profil.abonnement_id,
        "ticket_id": profil.ticket_id,
        "user_id": profil.user_id,
        "poste_id": profil.poste_id,
        "download_mbps": profil.download_mbps,
        "upload_mbps": profil.upload_mbps,
        "quota_journalier_mo": profil.quota_journalier_mo,
        "quota_mensuel_mo": profil.quota_mensuel_mo,
        "bloquer_si_depasse": profil.bloquer_si_depasse,
    }


def _serialize_usage(usage: BandePassanteUsage) -> dict:
    return {
        "id": usage.id,
        "session_id": usage.session_id,
        "ticket_id": usage.ticket_id,
        "user_id": usage.user_id,
        "data_download_mo": usage.data_download_mo,
        "data_upload_mo": usage.data_upload_mo,
        "data_total_mo": usage.data_total_mo,
        "date_enregistrement": usage.date_enregistrement,
    }


@router.post("/profils", status_code=201)
def definir_profil(data: BandePassanteProfilCreate, db: Session = Depends(get_db)):
    profil = BandePassanteService.definir_profil(db=db, **data.model_dump())
    return {"status_code": 201, "data": _serialize_profil(profil)}


@router.get("/profils/applicable")
def get_profil_applicable(
    user_id: int | None = None,
    ticket_id: int | None = None,
    poste_id: int | None = None,
    abonnement_id: int | None = None,
    offre_id: int | None = None,
    db: Session = Depends(get_db)
):
    profil = BandePassanteService.get_profil_applicable(
        db=db, user_id=user_id, ticket_id=ticket_id, poste_id=poste_id,
        abonnement_id=abonnement_id, offre_id=offre_id
    )
    return {"status_code": 200, "data": _serialize_profil(profil) if profil else None}


@router.post("/usage")
def enregistrer_usage(
    download_mo: float,
    upload_mo: float,
    session_id: int | None = None,
    user_id: int | None = None,
    ticket_id: int | None = None,
    db: Session = Depends(get_db)
):
    usage = BandePassanteService.enregistrer_usage(
        db=db, session_id=session_id, user_id=user_id, ticket_id=ticket_id,
        download_mo=download_mo, upload_mo=upload_mo
    )
    return {"status_code": 201, "data": _serialize_usage(usage)}


@router.get("/consommation")
def get_consommation(user_id: int | None = None, ticket_id: int | None = None, db: Session = Depends(get_db)):
    return {"status_code": 200, "data": BandePassanteService.get_consommation(db=db, user_id=user_id, ticket_id=ticket_id)}


@router.get("/usages")
def get_usages(
    user_id: int | None = None,
    ticket_id: int | None = None,
    session_id: int | None = None,
    db: Session = Depends(get_db)
):
    usages = BandePassanteService.get_usages(db=db, user_id=user_id, ticket_id=ticket_id, session_id=session_id)
    return {"status_code": 200, "data": [_serialize_usage(u) for u in usages]}


@router.post("/verifier-blocage")
def verifier_blocage(
    user_id: int | None = None,
    ticket_id: int | None = None,
    poste_id: int | None = None,
    db: Session = Depends(get_db)
):
    profil = BandePassanteService.get_profil_applicable(db=db, user_id=user_id, ticket_id=ticket_id, poste_id=poste_id)
    if not profil:
        return {"status_code": 200, "data": {"bloque": False, "detail": "Aucun profil de bande passante applicable"}}

    bloque = BandePassanteService.appliquer_blocage(db=db, profil=profil, user_id=user_id, ticket_id=ticket_id)
    return {"status_code": 200, "data": {"bloque": bloque}}
