from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import UserRole
from models.poste import Poste, PosteEtat, TypePoste
from schemas.poste_schema import PosteCreate, PosteUpdate
from services.Poste_service import PosteService
from services.historique_service import HistoriqueService
from dependencies.auth import auth_dependency
from dependencies.access import require_roles, require_permission, get_current_user
from utils.wol import envoyer_magic_packet


router = APIRouter(prefix="/poste", tags=["postes"], dependencies=[Depends(auth_dependency)])


def _serialize_session_brief(session) -> dict | None:
    if not session:
        return None
    return {
        "id": session.id,
        "user_id": session.user_id,
        "ticket_id": session.ticket_id,
        "limite_minutes": session.limite_minutes,
        "consommation_minutes": session.consommation_minutes,
        "limite_data_mo": session.limite_data_mo,
        "consommation_data_mo": session.consommation_data_mo,
    }


def _serialize(poste: Poste, db: Session | None = None) -> dict:
    return {
        "id": poste.id,
        "nom": poste.nom,
        "description": poste.description,
        "type_poste": poste.type_poste,
        "etat": poste.etat,
        "ip": poste.ip,
        "mac_adresse": poste.mac_adresse,
        "hostname": poste.hostname,
        "os": poste.os,
        "est_verrouille": poste.est_verrouille,
        "est_en_ligne": poste.est_en_ligne,
        "derniere_activite": poste.derniere_activite,
        "version_client": poste.version_client,
        "session_active": (
            _serialize_session_brief(PosteService.get_session_active(db=db, poste_id=poste.id))
            if db is not None else None
        ),
    }


@router.post("/", status_code=201, dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def creer_poste(data: PosteCreate, db: Session = Depends(get_db)):
    try:
        poste = PosteService.creer_poste(db=db, **data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # le token n'est renvoyé qu'ici, à la création : à saisir une fois dans le client desktop
    return {"status_code": 201, "data": {**_serialize(poste, db), "token": poste.token}}


@router.post("/{poste_id}/regenerer-token", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def regenerer_token(poste_id: int, db: Session = Depends(get_db)):
    try:
        poste = PosteService.regenerer_token(db=db, poste_id=poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": {**_serialize(poste, db), "token": poste.token}}


@router.get("/", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def lister_postes(etat: PosteEtat | None = None, type_poste: TypePoste | None = None, db: Session = Depends(get_db)):
    query = db.query(Poste)
    if etat is not None:
        query = query.filter(Poste.etat == etat)
    if type_poste is not None:
        query = query.filter(Poste.type_poste == type_poste)

    postes = query.order_by(Poste.nom.asc()).all()
    return {"status_code": 200, "data": [_serialize(p, db) for p in postes]}


@router.get("/{poste_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_poste(poste_id: int, db: Session = Depends(get_db)):
    poste = db.query(Poste).get(poste_id)
    if not poste:
        raise HTTPException(status_code=404, detail="Poste introuvable")

    return {"status_code": 200, "data": _serialize(poste, db)}


@router.get("/{poste_id}/session-active", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur]))])
def get_session_active(poste_id: int, db: Session = Depends(get_db)):
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    return {"status_code": 200, "data": {"session_id": session.id} if session else None}


@router.patch("/{poste_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def update_poste(poste_id: int, data: PosteUpdate, db: Session = Depends(get_db)):
    try:
        poste = PosteService.mettre_a_jour_poste(db=db, poste_id=poste_id, data=data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(poste, db)}


@router.patch("/{poste_id}/verrouiller", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("postes"))])
def verrouiller_poste(poste_id: int, db: Session = Depends(get_db)):
    try:
        poste = PosteService.verrouiller_poste(db=db, poste_id=poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(poste, db)}


@router.patch("/{poste_id}/deverrouiller", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("postes"))])
def deverrouiller_poste(poste_id: int, db: Session = Depends(get_db)):
    try:
        poste = PosteService.deverrouiller_poste(db=db, poste_id=poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(poste, db)}


@router.post("/{poste_id}/heartbeat")
def heartbeat(
    poste_id: int, version_client: str | None = None,
    ip: str | None = None, mac_adresse: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        poste = PosteService.heartbeat(
            db=db, poste_id=poste_id, version_client=version_client, ip=ip, mac_adresse=mac_adresse,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": _serialize(poste, db)}


@router.post("/{poste_id}/commande", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("postes"))])
def envoyer_commande(poste_id: int, commande: str, details: dict | None = Body(default=None), db: Session = Depends(get_db)):
    """Commandes reconnues par le client (voir client/core/system_commands.py) :
    "redemarrer", "eteindre" (sans details), "verrouiller_lecteur"/"deverrouiller_lecteur"
    (details={"identifiant": "E" sur Windows, ou un point de montage sur Linux})."""
    try:
        result = PosteService.envoyer_commande(db=db, poste_id=poste_id, commande=commande, details=details)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": result}


@router.post("/{poste_id}/desactiver-kiosque", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("postes"))])
def desactiver_kiosque(poste_id: int, db: Session = Depends(get_db)):
    """Désactive le kiosk à distance si le poste est actuellement connecté (voir
    PosteService.desactiver_kiosque) — équivalent distant de la désactivation
    locale par compte admin Windows sur le poste lui-même."""
    try:
        result = PosteService.desactiver_kiosque(db=db, poste_id=poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": result}


@router.post("/{poste_id}/code-secours", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("postes"))])
def generer_code_secours(poste_id: int, db: Session = Depends(get_db)):
    """Génère un code de secours à usage unique (déverrouillage admin local hors-ligne
    du kiosk) — voir PosteService.generer_code_secours. Le code en clair n'est renvoyé
    qu'ici, une seule fois : à communiquer immédiatement par téléphone à l'opérateur
    sur place, il n'est plus jamais récupérable ensuite."""
    try:
        result = PosteService.generer_code_secours(db=db, poste_id=poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": result}


@router.post("/verifier-hors-ligne", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def verifier_postes_hors_ligne(timeout_seconds: int = 30, db: Session = Depends(get_db)):
    postes = PosteService.verifier_postes_hors_ligne(db=db, timeout_seconds=timeout_seconds)
    return {"status_code": 200, "data": [_serialize(p, db) for p in postes]}


@router.delete("/{poste_id}", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin]))])
def supprimer_poste(poste_id: int, db: Session = Depends(get_db)):
    try:
        PosteService.supprimer_poste(db=db, poste_id=poste_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 200, "data": 1}


@router.post("/{poste_id}/reveil", dependencies=[Depends(require_roles(allowed_roles=[UserRole.admin, UserRole.operateur])), Depends(require_permission("postes"))])
def reveiller_poste(poste_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Wake-on-LAN : réveille un poste éteint via un paquet magique envoyé à son adresse
    MAC. Nécessite que le poste ait une adresse MAC enregistrée et le WOL activé côté
    matériel — voir utils/wol.py."""
    poste = db.query(Poste).get(poste_id)
    if not poste:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if not poste.mac_adresse:
        raise HTTPException(status_code=400, detail="Ce poste n'a pas d'adresse MAC enregistrée")

    try:
        envoyer_magic_packet(poste.mac_adresse)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    HistoriqueService.log(
        db=db, type_evenement="poste_wol",
        description=f"Signal de réveil (Wake-on-LAN) envoyé au poste '{poste.nom}'",
        operateur_id=user["id"], poste_id=poste_id,
    )

    return {"status_code": 200, "data": 1}
