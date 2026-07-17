from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.database import get_db
from models.user import User, UserRole
from models.abonnement import Abonnement
from models.article import Article
from models.offre import Offre
from models.paiement import Paiement
from models.impression import Impression
from models.session import Session as SessionModel
from models.chat_message import ExpediteurChat

from services.portail_service import PortailService, LimiteSessionsAtteinteError
from services.chat_service import ChatService
from services.config_service import ConfigService
from services.stockage_service import StockageService
from services.article_service import ArticleService

from dependencies.auth import auth_dependency
from dependencies.access import require_roles, get_current_user, get_current_ticket
from websocket.manager import manager


router = APIRouter(prefix="/portail", tags=["portail wifi"])

# Le portail sert deux publics : des visiteurs anonymes (achat de ticket, recharge,
# connexion par code ticket) et des clients connectés (JWT rôle client). Les
# endpoints publics sont sous /public et /wifi ; tout le reste exige le rôle client.
client_requis = [Depends(auth_dependency), Depends(require_roles(allowed_roles=[UserRole.client]))]

# Session ticket (portail en mode anonyme, connecté par code plutôt que par compte) —
# donne accès à un sous-ensemble de fonctionnalités dédiées (chat, impression), voir
# dependencies/access.py::get_current_ticket. Séparé de client_requis : un ticket
# n'est pas un User, ces deux jetons ne s'authentifient jamais l'un pour l'autre.
ticket_requis = [Depends(auth_dependency), Depends(get_current_ticket)]


def _erreur_limite_sessions(e: LimiteSessionsAtteinteError) -> HTTPException:
    """Traduit LimiteSessionsAtteinteError en 409 structuré : le client (portail ou
    kiosque) peut ainsi proposer explicitement de déconnecter cette session précise
    (en renvoyant la même requête avec deconnecter_session_id) plutôt que de deviner
    depuis un message d'erreur texte."""
    s = e.session
    return HTTPException(status_code=409, detail={
        "code": "limite_sessions_atteinte",
        "portee": e.portee,
        "limite": e.limite,
        "session_a_deconnecter": {
            "id": s.id,
            "poste_nom": s.poste.nom if s.poste else None,
            "date_debut": s.date_debut.isoformat() if s.date_debut else None,
        },
    })


# =============================================================
# PARTIE PUBLIQUE (aucune authentification)
# =============================================================

@router.get("/public/config")
def config_publique(db: Session = Depends(get_db)):
    """Habillage du portail (nom, logo, devise) — sous-ensemble public de la
    configuration, sans les informations internes."""
    config = ConfigService.get_config(db)
    return {"status_code": 200, "data": {
        "nom": config.get("cybercafe.nom"),
        "logo": config.get("cybercafe.logo"),
        "devise": config.get("cybercafe.devise"),
        "adresse": config.get("cybercafe.adresse"),
        "telephone": config.get("cybercafe.telephone"),
        "taux_tva": config.get("cybercafe.taux_tva"),
        "charte": config.get("cybercafe.charte"),
        "titre_accueil": config.get("portail.titre_accueil"),
        "texte_accueil": config.get("portail.texte_accueil"),
        "message_info": config.get("portail.message_info"),
        "message_connexion": config.get("portail.message_connexion"),
    }}


@router.get("/public/annonces")
def annonces_publiques(db: Session = Depends(get_db)):
    """Annonces d'information diffusées par l'équipe (bannière du portail) —
    lignes broadcast (toutes cibles NULL) destinées au wifi, les 5 plus récentes."""
    from models.notification import Notification
    annonces = (
        db.query(Notification)
        .filter(
            Notification.user_id == None, Notification.ticket_id == None,
            Notification.poste_id == None, Notification.operateur_id == None,
        )
        .order_by(Notification.date_creation.desc())
        .limit(5)
        .all()
    )
    return {"status_code": 200, "data": [{
        "id": n.id, "titre": n.titre, "message": n.message,
        "date": n.date_creation,
    } for n in annonces if (n.details or {}).get("cible") in ("wifi", "tous")]}


def _serialize_offre(offre: Offre) -> dict:
    return {
        "id": offre.id,
        "nom": offre.nom,
        "description": offre.description,
        "type_offre": offre.type_offre,
        "prix": offre.prix,
        "duree_minutes": getattr(offre, "duree_minutes", None),
        "quota_mo": getattr(offre, "quota_mo", None),
        "unite_duree": offre.unite_duree,
        "valeur_duree": offre.valeur_duree,
    }


@router.get("/public/offres")
def offres_publiques(db: Session = Depends(get_db)):
    offres = db.query(Offre).filter(Offre.is_actif == True).all()
    return {"status_code": 200, "data": [_serialize_offre(o) for o in offres]}


class CommandeTicket(BaseModel):
    offre_id: int
    gateway: str = "paypal"


@router.post("/public/ticket/commande", status_code=201)
def commander_ticket(data: CommandeTicket, db: Session = Depends(get_db)):
    try:
        result = PortailService.commander_ticket(db, offre_id=data.offre_id, gateway_nom=data.gateway)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": result}


class CommandeRechargePublique(BaseModel):
    username: str
    montant: float
    gateway: str = "paypal"


@router.post("/public/recharge/commande", status_code=201)
def commander_recharge_publique(data: CommandeRechargePublique, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    try:
        result = PortailService.commander_recharge(db, user_id=user.id, montant=data.montant, gateway_nom=data.gateway)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": result}


@router.get("/public/commande/{paiement_id}/statut")
def statut_commande(paiement_id: int, secret: str, db: Session = Depends(get_db)):
    try:
        return {"status_code": 200, "data": PortailService.statut_commande(db, paiement_id, secret)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ConfirmationDemo(BaseModel):
    secret: str


@router.post("/public/commande/{paiement_id}/confirmer-demo")
def confirmer_demo(paiement_id: int, data: ConfirmationDemo, db: Session = Depends(get_db)):
    """Simule le retour de redirection d'une passerelle réelle pour la passerelle
    démo (développement/test) — protégé par le secret par commande."""
    from services.paiement_service import PaiementService
    try:
        paiement = PaiementService.confirmer_commande_demo(db, paiement_id, data.secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": {"paiement_id": paiement.id, "statut": paiement.statut}}


# =============================================================
# SESSION WIFI PAR CODE TICKET (le code fait office d'identifiant)
# =============================================================

class CodeTicket(BaseModel):
    code: str
    deconnecter_session_id: int | None = None


@router.post("/wifi/connexion")
def wifi_connexion_ticket(data: CodeTicket, request: Request, db: Session = Depends(get_db)):
    from utils.security import create_access_token

    try:
        session = PortailService.demarrer_ticket(
            db, data.code, ip_client=request.client.host if request.client else None,
            deconnecter_session_id=data.deconnecter_session_id,
        )
    except LimiteSessionsAtteinteError as e:
        raise _erreur_limite_sessions(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Jeton de session ticket (mode anonyme) — donne accès au chat et à l'impression
    # dédiés au mode ticket (voir ticket_requis plus bas). Longue durée (24h) : pas de
    # mécanisme de refresh en mode anonyme, et une session ticket peut durer aussi
    # longtemps que le forfait lui-même.
    token = create_access_token({"ticket_id": session.ticket_id, "type": "ticket"}, expire=1440)

    return {"status_code": 200, "data": {**PortailService.serialiser_session(session), "token": token}}


@router.get("/wifi/etat")
def wifi_etat_ticket(code: str, db: Session = Depends(get_db)):
    from models.ticket import Ticket
    ticket = db.query(Ticket).filter(Ticket.code == code.strip().upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Code ticket inconnu")
    session = PortailService.session_active_ticket(db, ticket.id)
    if not session:
        return {"status_code": 200, "data": None}
    session = PortailService.actualiser(db, session)
    return {"status_code": 200, "data": PortailService.serialiser_session(session)}


@router.post("/wifi/deconnexion")
def wifi_deconnexion_ticket(data: CodeTicket, db: Session = Depends(get_db)):
    from models.ticket import Ticket
    ticket = db.query(Ticket).filter(Ticket.code == data.code.strip().upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Code ticket inconnu")
    session = PortailService.session_active_ticket(db, ticket.id)
    if session:
        PortailService.actualiser(db, session)
        if session.est_active:
            PortailService.terminer(db, session)
    return {"status_code": 200, "data": PortailService.serialiser_session(session) if session else None}


# =============================================================
# ESPACE CLIENT (JWT rôle client)
# =============================================================

def _serialize_abonnement(abo: Abonnement | None) -> dict | None:
    if not abo or not abo.est_actif:
        return None
    return {
        "id": abo.id,
        "offre_nom": abo.offre.nom if abo.offre else None,
        "date_debut": abo.date_debut,
        "date_fin": abo.date_fin,
        "est_suspendu": abo.est_suspendu,
        "illimite": abo.illimite,
        "minutes_par_jour": abo.minutes_par_jour,
        "minutes_restantes_aujourdhui": abo.minutes_restantes_aujourdhui,
        "data_totale_mo": abo.data_totale_mo,
        "data_restante_mo": abo.data_restante_mo,
    }


@router.get("/moi", dependencies=client_requis)
def mon_profil(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).get(currentuser["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    quota_mo = StockageService.get_quota_mo(db=db, user_id=user.id)
    usage_octets = StockageService.get_usage_octets(db=db, user_id=user.id)

    return {"status_code": 200, "data": {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "address": user.address,
        "date_of_born": user.date_of_born,
        "solde_euros": user.solde_euros,
        "date_create": user.date_create,
        "abonnement_courant": _serialize_abonnement(user.current_abonnement),
        "stockage": {"quota_mo": quota_mo, "usage_octets": usage_octets},
        "charte_acceptee": user.charte_acceptee_le is not None,
    }}


@router.post("/moi/accepter-charte", dependencies=client_requis)
def accepter_charte(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime
    user = db.query(User).get(currentuser["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if user.charte_acceptee_le is None:
        user.charte_acceptee_le = datetime.utcnow()
        db.commit()
    return {"status_code": 200, "data": {"charte_acceptee": True}}


@router.get("/mes-forfaits", dependencies=client_requis)
def mes_forfaits(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Tous les forfaits actifs du client (pas seulement le courant)."""
    from datetime import datetime
    abos = (
        db.query(Abonnement)
        .filter(Abonnement.user_id == currentuser["id"], Abonnement.est_actif == True)
        .order_by(Abonnement.date_debut.desc())
        .all()
    )
    maintenant = datetime.utcnow()
    actifs = [a for a in abos if a.date_fin is None or a.date_fin >= maintenant]
    return {"status_code": 200, "data": [_serialize_abonnement(a) for a in actifs]}


@router.get("/achats", dependencies=client_requis)
def mes_achats(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Historique d'achats du client : articles (avec suivi de commande jusqu'à la
    récupération) et forfaits, du plus récent au plus ancien."""
    from models.achat_article import AchatArticle
    from models.achat import Achat

    articles = (
        db.query(AchatArticle)
        .filter(AchatArticle.user_id == currentuser["id"])
        .order_by(AchatArticle.date_achat.desc())
        .limit(100)
        .all()
    )
    forfaits = (
        db.query(Achat)
        .filter(Achat.user_id == currentuser["id"])
        .order_by(Achat.date_achat.desc())
        .limit(100)
        .all()
    )
    return {"status_code": 200, "data": {
        "articles": [{
            "id": a.id,
            "article_nom": a.article.nom if a.article else None,
            "prix": a.prix,
            "date_achat": a.date_achat,
            "statut_commande": a.statut_commande,
            "paiement_id": a.paiement_id,
        } for a in articles],
        "forfaits": [{
            "id": f.id,
            "offre_nom": f.offre.nom if f.offre else None,
            "prix": getattr(f, "prix", None),
            "date_achat": f.date_achat,
        } for f in forfaits],
    }}


@router.get("/paiements/{paiement_id}/recu", dependencies=client_requis)
def telecharger_recu(paiement_id: int, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Ticket de caisse téléchargeable (HTML imprimable) pour un paiement du client."""
    from fastapi.responses import HTMLResponse
    from services.recu_service import RecuService

    paiement = db.query(Paiement).get(paiement_id)
    if not paiement or paiement.user_id != currentuser["id"]:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    html_recu = RecuService.generer_html(db, paiement)
    return HTMLResponse(
        content=html_recu,
        headers={"Content-Disposition": f'attachment; filename="recu-{paiement.id}.html"'},
    )


@router.get("/poste/recu/{paiement_id}")
def telecharger_recu_poste(paiement_id: int, poste_id: int, token: str, db: Session = Depends(get_db)):
    """Reçu téléchargeable depuis un poste kiosque : le poste s'authentifie par son
    token, et le paiement doit appartenir au client/ticket de la session active."""
    from fastapi.responses import HTMLResponse
    from services.Poste_service import PosteService
    from services.recu_service import RecuService

    poste = PosteService.authentifier_par_token(db=db, poste_id=poste_id, token=token)
    if not poste:
        raise HTTPException(status_code=401, detail="Poste ou token invalide")
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session:
        raise HTTPException(status_code=403, detail="Aucune session active sur ce poste")

    paiement = db.query(Paiement).get(paiement_id)
    if not paiement:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    proprietaire = (
        (session.user_id and paiement.user_id == session.user_id)
        or (session.ticket_id and paiement.ticket_id == session.ticket_id)
    )
    if not proprietaire:
        raise HTTPException(status_code=403, detail="Ce reçu n'appartient pas à la session en cours")

    html_recu = RecuService.generer_html(db, paiement)
    return HTMLResponse(
        content=html_recu,
        headers={"Content-Disposition": f'attachment; filename="recu-{paiement.id}.html"'},
    )


# --- Session WiFi (compte) ---

def _serialize_ticket_choix(t) -> dict:
    return {
        "id": t.id,
        "code": t.code,
        "offre_nom": t.offre.nom if t.offre else None,
        "restant_minutes": t.restant_minutes,
        "restant_data_mo": t.restant_data_mo,
        "date_expiration": t.date_expiration,
    }


@router.get("/mes-tickets", dependencies=client_requis)
def mes_tickets(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Tickets de connexion actifs rattachés au compte — un client peut en
    posséder plusieurs (achetés en caisse ou en ligne) et choisir lequel utiliser."""
    tickets = PortailService.tickets_actifs_user(db, currentuser["id"])
    return {"status_code": 200, "data": [_serialize_ticket_choix(t) for t in tickets]}


class DemarrerSession(BaseModel):
    ticket_id: int | None = None
    utiliser_abonnement: bool = False
    deconnecter_session_id: int | None = None


@router.post("/session/demarrer", dependencies=client_requis)
def demarrer_session(
    data: DemarrerSession = DemarrerSession(), request: Request = None,
    currentuser=Depends(get_current_user), db: Session = Depends(get_db),
):
    ip_client = request.client.host if request and request.client else None
    try:
        session = PortailService.demarrer_user(
            db, currentuser["id"], ticket_id=data.ticket_id, ip_client=ip_client,
            utiliser_abonnement=data.utiliser_abonnement,
            deconnecter_session_id=data.deconnecter_session_id,
        )
    except LimiteSessionsAtteinteError as e:
        raise _erreur_limite_sessions(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": PortailService.serialiser_session(session)}


@router.post("/session/changer-ticket", dependencies=client_requis)
def changer_ticket(
    data: DemarrerSession, request: Request,
    currentuser=Depends(get_current_user), db: Session = Depends(get_db),
):
    """Change de ticket (ou bascule vers l'abonnement) à tout moment : termine la
    session en cours (le temps déjà consommé reste débité du forfait précédent) et
    en démarre une nouvelle sur le forfait choisi."""
    session_courante = PortailService.session_active_user(db, currentuser["id"])
    if session_courante:
        PortailService.actualiser(db, session_courante)
        if session_courante.est_active:
            PortailService.terminer(db, session_courante)
    try:
        ip_client = request.client.host if request.client else None
        session = PortailService.demarrer_user(
            db, currentuser["id"], ticket_id=data.ticket_id, ip_client=ip_client,
            utiliser_abonnement=data.utiliser_abonnement,
            deconnecter_session_id=data.deconnecter_session_id,
        )
    except LimiteSessionsAtteinteError as e:
        raise _erreur_limite_sessions(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": PortailService.serialiser_session(session)}


@router.get("/session", dependencies=client_requis)
def session_courante(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    session = PortailService.session_active_user(db, currentuser["id"])
    if not session:
        return {"status_code": 200, "data": None}
    session = PortailService.actualiser(db, session)
    return {"status_code": 200, "data": PortailService.serialiser_session(session)}


@router.post("/session/terminer", dependencies=client_requis)
def terminer_session(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    session = PortailService.session_active_user(db, currentuser["id"])
    if not session:
        raise HTTPException(status_code=400, detail="Aucune session WiFi active")
    PortailService.actualiser(db, session)
    if session.est_active:
        PortailService.terminer(db, session)
    return {"status_code": 200, "data": PortailService.serialiser_session(session)}


# --- Suivi de consommation ---

@router.get("/consommation", dependencies=client_requis)
def ma_consommation(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == currentuser["id"])
        .order_by(SessionModel.date_debut.desc())
        .limit(100)
        .all()
    )
    total_minutes = sum(s.consommation_minutes or 0 for s in sessions)
    total_data = sum(s.consommation_data_mo or 0 for s in sessions)
    return {"status_code": 200, "data": {
        "total_minutes": total_minutes,
        "total_data_mo": total_data,
        "sessions": [{
            "id": s.id,
            "poste_nom": s.poste.nom if s.poste else None,
            "date_debut": s.date_debut,
            "date_fin": s.date_fin,
            "est_active": s.est_active,
            "consommation_minutes": s.consommation_minutes,
            "consommation_data_mo": s.consommation_data_mo,
        } for s in sessions],
    }}


# --- Boutique (articles + forfaits) et panier ---

@router.get("/articles", dependencies=client_requis)
def articles_boutique(db: Session = Depends(get_db)):
    articles = db.query(Article).filter(Article.actif == True).all()
    return {"status_code": 200, "data": [{
        "id": a.id,
        "nom": a.nom,
        "description": a.description,
        "prix": a.prix,
        "categorie_nom": a.categorie.nom if a.categorie else None,
        "categorie_emoji": a.categorie.emoji if a.categorie else None,
        "stock": a.stock,
        "en_rupture": a.stock is not None and a.stock <= 0,
        "a_une_image": a.image_cle_stockage is not None,
    } for a in articles]}


@router.get("/articles/{article_id}/image", dependencies=client_requis)
def image_article(article_id: int, db: Session = Depends(get_db)):
    try:
        article, flux = ArticleService.get_image(db=db, article_id=article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StreamingResponse(flux, media_type=article.image_content_type or "image/jpeg")


class LignePanier(BaseModel):
    type: str  # "article" | "forfait"
    id: int
    quantite: int = 1


class Panier(BaseModel):
    items: list[LignePanier]


@router.post("/panier/commander", dependencies=client_requis)
def commander_panier(data: Panier, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = PortailService.commander_panier(
            db, user_id=currentuser["id"], items=[item.model_dump() for item in data.items],
            statut_commande_articles="a_preparer",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": result}


# --- Paiements en ligne (compte connecté) ---

class CommandeRecharge(BaseModel):
    montant: float
    gateway: str = "paypal"


@router.post("/recharge/commande", status_code=201, dependencies=client_requis)
def commander_recharge(data: CommandeRecharge, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = PortailService.commander_recharge(
            db, user_id=currentuser["id"], montant=data.montant, gateway_nom=data.gateway,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": result}


class RechargeParCode(BaseModel):
    code: str


@router.post("/recharge/code", dependencies=client_requis)
def recharger_par_code(data: RechargeParCode, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Recharge du solde avec un bon de recharge (ticket crédit) acheté au comptoir."""
    from services.ticket_service import TicketService
    try:
        ticket, nouveau_solde = TicketService.utiliser_credit(db=db, code=data.code, user_iden=currentuser["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 200, "data": {"credit_euros": ticket.credit_euros, "nouveau_solde": nouveau_solde}}


class CommandeForfait(BaseModel):
    gateway: str = "paypal"


@router.post("/forfaits/{offre_id}/commande", status_code=201, dependencies=client_requis)
def commander_forfait(offre_id: int, data: CommandeForfait, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = PortailService.commander_offre(
            db, user_id=currentuser["id"], offre_id=offre_id, gateway_nom=data.gateway,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status_code": 201, "data": result}


@router.get("/paiements", dependencies=client_requis)
def mes_paiements(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Historique « tickets & factures » du compte : chaque paiement enrichi de la
    nature du produit réglé (forfait, article, recharge) — voir
    PortailService.lister_paiements_enrichis."""
    return {"status_code": 200, "data": PortailService.lister_paiements_enrichis(db, user_id=currentuser["id"])}


@router.get("/poste/paiements")
def mes_paiements_poste(poste_id: int, token: str, db: Session = Depends(get_db)):
    """Même historique, depuis un poste kiosque : le poste s'authentifie par son
    token, et l'historique est celui du compte (session ouverte par identifiants) ou
    du ticket (session anonyme par code) actuellement actif sur ce poste."""
    from services.Poste_service import PosteService

    poste = PosteService.authentifier_par_token(db=db, poste_id=poste_id, token=token)
    if not poste:
        raise HTTPException(status_code=401, detail="Poste ou token invalide")
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session:
        raise HTTPException(status_code=403, detail="Aucune session active sur ce poste")

    data = PortailService.lister_paiements_enrichis(db, user_id=session.user_id, ticket_id=session.ticket_id)
    return {"status_code": 200, "data": data}


# --- Impressions ---

def _prix_impression(db: Session, cle: str, defaut: float) -> float:
    """get_valeur lève une exception si le paramètre n'a jamais été initialisé —
    on retombe alors sur le tarif par défaut plutôt que d'échouer la demande."""
    from services.system_setting_service import SystemSettingsService
    try:
        return SystemSettingsService.get_valeur(db, cle) or defaut
    except ValueError:
        return defaut


@router.get("/impression/tarifs", dependencies=client_requis)
def tarifs_impression(db: Session = Depends(get_db)):
    return {"status_code": 200, "data": {
        "prix_nb": _prix_impression(db, "impression.prix_nb", 0.10),
        "prix_couleur": _prix_impression(db, "impression.prix_couleur", 0.25),
    }}


class DemandeImpression(BaseModel):
    fichier_id: int
    pages: int
    type_impression: str  # "noir_blanc" | "couleur"
    recto_verso: bool = False


@router.post("/impressions", status_code=201, dependencies=client_requis)
def demander_impression(data: DemandeImpression, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    """Demande d'impression depuis le portail : le document vient de l'espace de
    stockage personnel du client, et le prix par page est TOUJOURS celui des
    réglages système (jamais fourni par le client)."""
    from models.fichier_stocke import FichierStocke
    from models.impression import TypeImpression, OrigineImpression
    from services.impression_service import ImpressionService

    fichier = (
        db.query(FichierStocke)
        .filter(FichierStocke.id == data.fichier_id, FichierStocke.user_id == currentuser["id"])
        .first()
    )
    if not fichier:
        raise HTTPException(status_code=404, detail="Fichier introuvable dans votre espace de stockage")
    if data.pages < 1 or data.pages > 500:
        raise HTTPException(status_code=400, detail="Nombre de pages invalide")
    if data.type_impression not in (TypeImpression.NOIR_BLANC.value, TypeImpression.COULEUR.value):
        raise HTTPException(status_code=400, detail="Type d'impression invalide")

    if data.type_impression == TypeImpression.COULEUR.value:
        prix_par_page = _prix_impression(db, "impression.prix_couleur", 0.25)
    else:
        prix_par_page = _prix_impression(db, "impression.prix_nb", 0.10)

    try:
        impression = ImpressionService.creer_impression(
            db=db,
            origine=OrigineImpression.WIFI,
            fichier_nom=fichier.nom_original,
            fichier_path=fichier.cle_stockage,
            pages_liste=list(range(1, data.pages + 1)),
            type_impression=TypeImpression(data.type_impression),
            recto_verso=data.recto_verso,
            prix_par_page=prix_par_page,
            user_id=currentuser["id"],
            details={"fichier_stocke_id": fichier.id, "via": "portail"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Crédit suffisant : réglée immédiatement sur le solde. La demande reste EN_ATTENTE
    # (pas EN_COURS) une fois payée : c'est le worker de fond (voir
    # config/background_tasks.py -> ImpressionService.traiter_file_attente) qui
    # l'enverra réellement à l'imprimante configurée et fera avancer son statut.
    lancee_automatiquement = False
    user = db.query(User).get(currentuser["id"])
    if user and user.solde_euros >= (impression.prix_total or 0):
        try:
            impression = ImpressionService.payer_impression(db=db, impression_id=impression.id, utiliser_solde=True)
            lancee_automatiquement = True
        except ValueError:
            pass  # solde débité entre-temps : la demande reste en attente de règlement

    return {"status_code": 201, "data": {
        "id": impression.id,
        "lancee_automatiquement": lancee_automatiquement,
        "fichier_nom": impression.fichier_nom,
        "pages_total": impression.pages_total,
        "type_impression": impression.type_impression,
        "recto_verso": impression.recto_verso,
        "prix_total": impression.prix_total,
        "statut": impression.statut,
        "date_impression": impression.date_impression,
    }}


@router.get("/impressions", dependencies=client_requis)
def mes_impressions(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    impressions = (
        db.query(Impression)
        .filter(Impression.user_id == currentuser["id"])
        .order_by(Impression.date_impression.desc())
        .limit(50)
        .all()
    )
    return {"status_code": 200, "data": [{
        "id": i.id,
        "fichier_nom": i.fichier_nom,
        "pages_total": i.pages_total,
        "type_impression": i.type_impression,
        "recto_verso": i.recto_verso,
        "prix_total": i.prix_total,
        "statut": i.statut,
        "paye": i.paye,
        "date_impression": i.date_impression,
    } for i in impressions]}


# --- Impression en mode ticket (anonyme) : pas d'espace fichiers persistant ni de
# solde — le fichier est envoyé directement avec la demande, et le règlement se fait
# en espèces à l'accueil (la demande reste EN_ATTENTE / non payée jusqu'à ce qu'un
# opérateur l'encaisse, voir l'admin Impressions). ---

@router.post("/ticket/impressions", status_code=201, dependencies=ticket_requis)
async def ticket_demander_impression(
    file: UploadFile = File(...),
    pages: int = Form(...),
    type_impression: str = Form(...),
    recto_verso: bool = Form(False),
    currentticket=Depends(get_current_ticket),
    db: Session = Depends(get_db),
):
    from models.impression import TypeImpression, OrigineImpression
    from services.impression_service import ImpressionService

    if pages < 1 or pages > 500:
        raise HTTPException(status_code=400, detail="Nombre de pages invalide")
    if type_impression not in (TypeImpression.NOIR_BLANC.value, TypeImpression.COULEUR.value):
        raise HTTPException(status_code=400, detail="Type d'impression invalide")

    ticket_id = currentticket["ticket_id"]
    contenu = await file.read()
    try:
        fichier = StockageService.upload_fichier(
            db=db, contenu=contenu, nom_original=file.filename,
            content_type=file.content_type, ticket_id=ticket_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if type_impression == TypeImpression.COULEUR.value:
        prix_par_page = _prix_impression(db, "impression.prix_couleur", 0.25)
    else:
        prix_par_page = _prix_impression(db, "impression.prix_nb", 0.10)

    try:
        impression = ImpressionService.creer_impression(
            db=db,
            origine=OrigineImpression.WIFI,
            fichier_nom=fichier.nom_original,
            fichier_path=fichier.cle_stockage,
            pages_liste=list(range(1, pages + 1)),
            type_impression=TypeImpression(type_impression),
            recto_verso=recto_verso,
            prix_par_page=prix_par_page,
            ticket_id=ticket_id,
            details={"fichier_stocke_id": fichier.id, "via": "portail_ticket"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status_code": 201, "data": {
        "id": impression.id,
        "fichier_nom": impression.fichier_nom,
        "pages_total": impression.pages_total,
        "type_impression": impression.type_impression,
        "recto_verso": impression.recto_verso,
        "prix_total": impression.prix_total,
        "statut": impression.statut,
        "date_impression": impression.date_impression,
    }}


@router.get("/ticket/impressions", dependencies=ticket_requis)
def ticket_mes_impressions(currentticket=Depends(get_current_ticket), db: Session = Depends(get_db)):
    impressions = (
        db.query(Impression)
        .filter(Impression.ticket_id == currentticket["ticket_id"])
        .order_by(Impression.date_impression.desc())
        .limit(50)
        .all()
    )
    return {"status_code": 200, "data": [{
        "id": i.id,
        "fichier_nom": i.fichier_nom,
        "pages_total": i.pages_total,
        "type_impression": i.type_impression,
        "recto_verso": i.recto_verso,
        "prix_total": i.prix_total,
        "statut": i.statut,
        "paye": i.paye,
        "date_impression": i.date_impression,
    } for i in impressions]}


# --- Chat avec le gérant ---

def _serialize_chat(msg) -> dict:
    return {
        "id": msg.id,
        "expediteur": msg.expediteur.value if hasattr(msg.expediteur, "value") else msg.expediteur,
        "message": msg.message,
        "date_envoi": msg.date_envoi.isoformat(),
        "lu": msg.lu,
    }


@router.get("/chat", dependencies=client_requis)
def chat_historique(currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    messages = ChatService.historique_wifi(db, currentuser["id"])
    # côté client, les réponses de l'opérateur sont considérées lues dès affichage
    ChatService.marquer_lu_wifi(db, currentuser["id"], ExpediteurChat.OPERATEUR)
    return {"status_code": 200, "data": [_serialize_chat(m) for m in messages]}


class MessageChat(BaseModel):
    message: str


@router.post("/chat", status_code=201, dependencies=client_requis)
def chat_envoyer(data: MessageChat, currentuser=Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")
    msg = ChatService.envoyer_message_wifi(
        db, user_id=currentuser["id"], message=data.message.strip(),
        expediteur=ExpediteurChat.CLIENT,
    )
    payload = {
        **_serialize_chat(msg),
        "wifi_user_id": currentuser["id"],
        "wifi_username": currentuser.get("username"),
    }
    manager.broadcast_to_admins_threadsafe("chat_message_wifi", payload)
    return {"status_code": 201, "data": _serialize_chat(msg)}


# --- Chat en mode ticket (anonyme) : fil rattaché à la session active, éphémère
# (voir ChatService.purger_conversation_session, déclenché à la fin de la session). ---

def _session_active_pour_ticket(db: Session, ticket_id: int) -> SessionModel:
    session = PortailService.session_active_ticket(db, ticket_id)
    if not session:
        raise HTTPException(status_code=409, detail="Aucune session WiFi active pour ce ticket — connectez-vous d'abord")
    return session


@router.get("/ticket/chat", dependencies=ticket_requis)
def ticket_chat_historique(currentticket=Depends(get_current_ticket), db: Session = Depends(get_db)):
    session = _session_active_pour_ticket(db, currentticket["ticket_id"])
    messages = ChatService.historique_ticket(db, session.id)
    ChatService.marquer_lu_ticket(db, session.id, ExpediteurChat.OPERATEUR)
    return {"status_code": 200, "data": [_serialize_chat(m) for m in messages]}


@router.post("/ticket/chat", status_code=201, dependencies=ticket_requis)
def ticket_chat_envoyer(data: MessageChat, currentticket=Depends(get_current_ticket), db: Session = Depends(get_db)):
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")
    session = _session_active_pour_ticket(db, currentticket["ticket_id"])
    msg = ChatService.envoyer_message_ticket(
        db, session_id=session.id, message=data.message.strip(),
        expediteur=ExpediteurChat.CLIENT,
    )
    payload = {**_serialize_chat(msg), "session_id": session.id, "ticket_code": session.ticket.code if session.ticket else None}
    manager.broadcast_to_admins_threadsafe("chat_message_ticket", payload)
    return {"status_code": 201, "data": _serialize_chat(msg)}
