from datetime import date, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from config.database import SessionLocal
from models.poste import Poste
from models.user import User, is_validUser
from models.abonnement import is_valide_abonnement
from models.ticket import Ticket, TypeTicket, AccesTicket
from models.impression import OrigineImpression, TypeImpression
from services.Poste_service import PosteService, _serialize_poste_for_admin
from services.session_service import SessionService
from services.article_service import ArticleService
from services.impression_service import ImpressionService
from services.system_setting_service import SystemSettingsService
from services.app_bloquee_service import AppBloqueeService
from services.lecteur_bloque_service import LecteurBloqueService
from services.site_regle_service import SiteRegleService
from services.chat_service import ChatService
from services.pay_connect_service import PayConnectService
from utils.security import verify_password
from utils.logger import logger
from websocket.manager import manager


router = APIRouter()


def _serialize_session(session) -> dict:
    return {
        "id": session.id,
        "poste_id": session.poste_id,
        "user_id": session.user_id,
        "ticket_id": session.ticket_id,
        "limite_minutes": session.limite_minutes,
        "limite_data_mo": session.limite_data_mo,
        "consommation_minutes": session.consommation_minutes,
        "consommation_data_mo": session.consommation_data_mo,
    }


# ---------------------------------------------------------
# HANDLERS (fonctions synchrones, exécutées en threadpool pour ne pas
# bloquer la boucle asyncio partagée par tous les postes connectés)
# ---------------------------------------------------------

def _handle_session_request(db, poste_id: int, data: dict) -> dict:
    username = data.get("username")
    password = data.get("password")
    code = data.get("code")

    if (username is None) == (code is None):
        return {"type": "session_error", "data": {"message": "un seul des paramètres doit être saisi : username/password ou code"}}

    # Charte / conditions d'utilisation : si une charte est configurée, le client du
    # poste doit l'avoir acceptée (case cochée sur l'écran de connexion du kiosque).
    from services.config_service import ConfigService
    charte = (ConfigService.get_config(db) or {}).get("cybercafe.charte") or ""
    if charte.strip() and not data.get("charte_acceptee"):
        return {"type": "session_error", "data": {"message": "Vous devez accepter la charte d'utilisation pour vous connecter", "charte_requise": True}}

    user_id = None
    ticket_id = None
    abonnement_id = None

    if username is not None:
        user = db.query(User).filter(User.username == username).first()
        if user is None or not password or not verify_password(password, user.password):
            return {"type": "session_error", "data": {"message": "Identifiants incorrects"}}

        validuser = is_validUser(user=user)
        if not validuser["valide"]:
            return {"type": "session_error", "data": {"message": validuser["detail"]}}

        if data.get("charte_acceptee") and user.charte_acceptee_le is None:
            from datetime import datetime as _dt
            user.charte_acceptee_le = _dt.utcnow()
            db.commit()

        user_id = user.id
        abonnement_valide = user.current_abonnement and is_valide_abonnement(user.current_abonnement)["valide"]

        ticket_choisi_id = data.get("ticket_id")

        if ticket_choisi_id is not None:
            # le client a explicitement choisi un de ses tickets (menu de choix,
            # ou changement de ticket en cours d'utilisation)
            from services.portail_service import PortailService
            ticket_choisi = db.query(Ticket).get(ticket_choisi_id)
            if not ticket_choisi or ticket_choisi.user_id != user.id:
                return {"type": "session_error", "data": {"message": "Ce ticket n'appartient pas à ce compte"}}
            if ticket_choisi not in PortailService.tickets_actifs_user(db, user.id, contexte="poste"):
                return {"type": "session_error", "data": {"message": "Ce ticket n'est plus utilisable"}}
            ticket_id = ticket_choisi.id

        elif abonnement_valide:
            abonnement_id = user.current_abonnement_id

        else:
            from services.portail_service import PortailService
            tickets_dispo = PortailService.tickets_actifs_user(db, user.id, contexte="poste")
            if not tickets_dispo:
                if user.current_abonnement:
                    return {"type": "session_error", "data": {"message": is_valide_abonnement(user.current_abonnement)["detail"]}}
                return {"type": "session_error", "data": {"message": "Aucun abonnement actif n'est associé à ce compte"}}
            if len(tickets_dispo) == 1:
                ticket_id = tickets_dispo[0].id
            else:
                return {
                    "type": "tickets_choice_required",
                    "data": {
                        "username": username,
                        "tickets": [{
                            "id": t.id, "code": t.code,
                            "offre_nom": t.offre.nom if t.offre else None,
                            "restant_minutes": t.restant_minutes,
                            "restant_data_mo": t.restant_data_mo,
                        } for t in tickets_dispo],
                    },
                }

    if code is not None:
        ticket = db.query(Ticket).filter(Ticket.code == code).first()
        if ticket is None:
            return {"type": "session_error", "data": {"message": f"le ticket : {code} n'existe pas"}}
        if not ticket.est_actif or ticket.est_consomme:
            return {"type": "session_error", "data": {"message": f"le ticket : {code} n'est plus utilisable"}}
        if ticket.type_ticket == TypeTicket.CREDIT:
            return {"type": "session_error", "data": {"message": "Ce code est un bon de recharge, pas un ticket de connexion"}}
        if ticket.acces == AccesTicket.WIFI:
            return {"type": "session_error", "data": {"message": f"le ticket : {code} est réservé à l'accès WiFi"}}
        if ticket.date_expiration is not None and ticket.date_expiration.date() < date.today():
            return {"type": "session_error", "data": {"message": f"le ticket : {code} est expiré"}}
        if ticket.restant_minutes is not None and ticket.restant_minutes <= 5:
            return {"type": "session_error", "data": {"message": f"le ticket : {code} n'a plus assez de temps"}}
        if ticket.restant_data_mo is not None and ticket.restant_data_mo <= 10:
            return {"type": "session_error", "data": {"message": f"le ticket : {code} n'a plus assez de data"}}
        ticket_id = ticket.id

    from services.portail_service import PortailService, LimiteSessionsAtteinteError
    from models.abonnement import Abonnement

    ticket_obj = db.query(Ticket).get(ticket_id) if ticket_id is not None else None
    abonnement_obj = db.query(Abonnement).get(abonnement_id) if abonnement_id is not None else None
    user_obj = db.query(User).get(user_id) if user_id is not None else None

    try:
        PortailService.verifier_limite_sessions(
            db, ticket=ticket_obj, abonnement=abonnement_obj, user=user_obj,
            deconnecter_session_id=data.get("deconnecter_session_id"),
        )
    except LimiteSessionsAtteinteError as e:
        s = e.session
        return {
            "type": "session_limit_reached",
            "data": {
                "portee": e.portee,
                "limite": e.limite,
                "session_a_deconnecter": {
                    "id": s.id,
                    "poste_nom": s.poste.nom if s.poste else None,
                    "date_debut": s.date_debut.isoformat() if s.date_debut else None,
                },
                # renvoyés tels quels pour que le kiosque puisse soumettre à nouveau
                # exactement la même demande de connexion, avec deconnecter_session_id cette fois
                "username": username, "code": code, "ticket_id": ticket_id,
            },
        }

    try:
        session = SessionService.demarrer_session(
            db=db, poste_id=poste_id, user_id=user_id, ticket_id=ticket_id, abonnement_id=abonnement_id
        )
    except ValueError as e:
        return {"type": "session_error", "data": {"message": str(e)}}

    return {"type": "session_started", "data": _serialize_session(session)}


def _handle_session_end_request(db, poste_id: int, data: dict) -> dict:
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session:
        return {"type": "session_error", "data": {"message": "Aucune session active sur ce poste"}}

    try:
        SessionService.fermer_session(db=db, session_id=session.id)
    except ValueError as e:
        return {"type": "session_error", "data": {"message": str(e)}}

    return {"type": "session_ended", "data": {"reason": "demande_client"}}


def _handle_changer_ticket_request(db, poste_id: int, data: dict) -> dict:
    """Change de ticket à tout moment sur un poste kiosque : termine la session en
    cours (rattachée à un compte) et en démarre une nouvelle sur le ticket choisi,
    sans redemander les identifiants."""
    from services.portail_service import PortailService

    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session or not session.user_id:
        return {"type": "session_error", "data": {"message": "Aucune session de compte active sur ce poste"}}

    ticket_id = data.get("ticket_id")
    ticket_choisi = db.query(Ticket).get(ticket_id) if ticket_id else None
    if not ticket_choisi or ticket_choisi.user_id != session.user_id:
        return {"type": "session_error", "data": {"message": "Ce ticket n'appartient pas à ce compte"}}
    if ticket_choisi not in PortailService.tickets_actifs_user(db, session.user_id, contexte="poste"):
        return {"type": "session_error", "data": {"message": "Ce ticket n'est plus utilisable"}}

    user_id = session.user_id
    try:
        SessionService.fermer_session(db=db, session_id=session.id)
        nouvelle_session = SessionService.demarrer_session(
            db=db, poste_id=poste_id, user_id=user_id, ticket_id=ticket_choisi.id
        )
    except ValueError as e:
        return {"type": "session_error", "data": {"message": str(e)}}

    return {"type": "session_started", "data": _serialize_session(nouvelle_session)}


def _handle_mes_tickets_request(db, poste_id: int, data: dict) -> dict:
    """Liste des tickets utilisables du compte actuellement connecté sur ce poste
    (pour proposer un changement de ticket en cours de session)."""
    from services.portail_service import PortailService

    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session or not session.user_id:
        return {"type": "mes_tickets", "data": {"tickets": []}}

    tickets = PortailService.tickets_actifs_user(db, session.user_id, contexte="poste")
    return {"type": "mes_tickets", "data": {"tickets": [{
        "id": t.id, "code": t.code,
        "offre_nom": t.offre.nom if t.offre else None,
        "restant_minutes": t.restant_minutes,
        "restant_data_mo": t.restant_data_mo,
    } for t in tickets]}}


def _handle_list_articles(db, poste_id: int, data: dict) -> dict:
    articles = ArticleService.rechercher_articles(db=db, actif=True)
    return {
        "type": "articles_list",
        "data": {
            "articles": [
                {
                    "id": a.id, "nom": a.nom, "prix": a.prix, "description": a.description,
                    "categorie_nom": a.categorie.nom if a.categorie else None,
                    "categorie_emoji": a.categorie.emoji if a.categorie else None,
                }
                for a in articles
            ]
        }
    }


def _handle_buy_article(db, poste_id: int, data: dict) -> dict:
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    if not session or not session.user_id:
        return {"type": "purchase_result", "data": {"success": False, "message": "Aucune session client active sur ce poste"}}

    try:
        result = ArticleService.acheter_article(
            db=db,
            article_id=data.get("article_id"),
            user_id=session.user_id,
            utiliser_solde=True,
            code_promo=data.get("code_promo")
        )
    except ValueError as e:
        return {"type": "purchase_result", "data": {"success": False, "message": str(e)}}

    user = db.query(User).get(session.user_id)
    return {
        "type": "purchase_result",
        "data": {"success": True, "message": "Achat effectué", "achat": result, "nouveau_solde": user.solde_euros}
    }


def _handle_print_billing(db, poste_id: int, data: dict) -> dict:
    session = PosteService.get_session_active(db=db, poste_id=poste_id)
    user_id = session.user_id if session else None

    try:
        type_impression = TypeImpression(data.get("type_impression", "noir_blanc"))
    except ValueError:
        type_impression = TypeImpression.NOIR_BLANC

    cle_prix = "impression.prix_couleur" if type_impression == TypeImpression.COULEUR else "impression.prix_nb"
    try:
        prix_par_page = SystemSettingsService.get_valeur(db, cle_prix)
    except ValueError:
        prix_par_page = 0.10

    pages_total = max(1, int(data.get("pages_total", 1)))

    try:
        impression = ImpressionService.creer_impression(
            db=db,
            origine=OrigineImpression.POSTE,
            fichier_nom=data.get("fichier_nom", "document"),
            fichier_path="(impression locale sur le poste)",
            pages_liste=list(range(1, pages_total + 1)),
            type_impression=type_impression,
            recto_verso=bool(data.get("recto_verso", False)),
            prix_par_page=prix_par_page,
            user_id=user_id,
            poste_id=poste_id
        )
        if user_id:
            ImpressionService.payer_impression(db=db, impression_id=impression.id, utiliser_solde=True)
        ImpressionService.terminer_impression(db=db, impression_id=impression.id)
    except ValueError as e:
        return {"type": "print_result", "data": {"success": False, "message": str(e)}}

    return {
        "type": "print_result",
        "data": {"success": True, "message": "Impression facturée", "prix_total": impression.prix_total}
    }


def _handle_chat_message(db, poste_id: int, data: dict) -> dict:
    message = (data.get("message") or "").strip()
    if not message:
        return {"type": "error", "data": {"message": "message vide"}}

    msg = ChatService.envoyer_message_client(db=db, poste_id=poste_id, message=message)
    payload = {
        "id": msg.id,
        "poste_id": msg.poste_id,
        "expediteur": msg.expediteur,
        "operateur_id": msg.operateur_id,
        "message": msg.message,
        "date_envoi": msg.date_envoi.isoformat(),
        "lu": msg.lu,
        "piece_jointe_nom": msg.piece_jointe_nom,
        "piece_jointe_taille_octets": msg.piece_jointe_taille_octets,
        "piece_jointe_content_type": msg.piece_jointe_content_type,
    }
    manager.broadcast_to_admins_threadsafe("chat_message", payload)
    return {"type": "chat_message", "data": payload}


def _handle_pay_connect_tarifs(db, poste_id: int, data: dict) -> dict:
    return {"type": "pay_connect_tarifs", "data": {"tarifs": PayConnectService.lister_tarifs(db)}}


def _handle_pay_connect_solde(db, poste_id: int, data: dict) -> dict:
    try:
        session = PayConnectService.demarrer_avec_solde(
            db=db, poste_id=poste_id,
            username=data.get("username"), password=data.get("password"), minutes=data.get("minutes"),
        )
    except ValueError as e:
        return {"type": "pay_connect_error", "data": {"message": str(e)}}

    return {"type": "session_started", "data": _serialize_session(session)}


def _handle_pay_connect_request(db, poste_id: int, data: dict) -> dict:
    try:
        demande = PayConnectService.creer_demande(db=db, poste_id=poste_id, minutes=data.get("minutes"))
    except ValueError as e:
        return {"type": "pay_connect_error", "data": {"message": str(e)}}

    return {
        "type": "pay_connect_pending",
        "data": {"id": demande.id, "minutes": demande.minutes, "montant": demande.montant}
    }


def _handle_pay_connect_cancel(db, poste_id: int, data: dict) -> dict:
    try:
        PayConnectService.annuler_demande(db=db, request_id=data.get("id"), poste_id=poste_id)
    except ValueError as e:
        return {"type": "pay_connect_error", "data": {"message": str(e)}}

    return {"type": "pay_connect_cancelled", "data": {"id": data.get("id")}}


HANDLERS = {
    "session_request": _handle_session_request,
    "session_end_request": _handle_session_end_request,
    "list_articles_request": _handle_list_articles,
    "buy_article": _handle_buy_article,
    "print_billing": _handle_print_billing,
    "chat_message": _handle_chat_message,
    "pay_connect_tarifs_request": _handle_pay_connect_tarifs,
    "pay_connect_solde": _handle_pay_connect_solde,
    "pay_connect_request": _handle_pay_connect_request,
    "pay_connect_cancel": _handle_pay_connect_cancel,
    "changer_ticket_request": _handle_changer_ticket_request,
    "mes_tickets_request": _handle_mes_tickets_request,
}


# ---------------------------------------------------------
# ENDPOINT WEBSOCKET
# ---------------------------------------------------------
@router.websocket("/ws/poste/{poste_id}")
async def poste_websocket(websocket: WebSocket, poste_id: int, token: str):
    db = SessionLocal()
    try:
        poste = await run_in_threadpool(PosteService.authentifier_par_token, db, poste_id, token)
        if not poste:
            await websocket.close(code=4401)
            return

        await manager.connect(websocket, poste_id)
        await run_in_threadpool(PosteService.heartbeat, db, poste_id, None)

        active_session = await run_in_threadpool(PosteService.get_session_active, db, poste_id)
        await websocket.send_json({
            "type": "paired",
            "data": {
                "poste_id": poste_id,
                "poste_nom": poste.nom,
                "session": _serialize_session(active_session) if active_session else None
            }
        })

        apps_bloquees = await run_in_threadpool(AppBloqueeService.get_regles_pour_poste, db, poste_id)
        await websocket.send_json({"type": "blocked_apps", "data": {"apps": apps_bloquees}})

        domaines_bloques = await run_in_threadpool(SiteRegleService.get_domaines_pour_session, db, poste_id)
        await websocket.send_json({"type": "blocked_sites", "data": {"domaines": domaines_bloques}})

        types_lecteurs_bloques = await run_in_threadpool(LecteurBloqueService.get_regles_pour_poste, db, poste_id)
        await websocket.send_json({"type": "blocked_drives", "data": {"types": types_lecteurs_bloques}})

        chat_historique = await run_in_threadpool(ChatService.historique, db, poste_id, 50)
        await websocket.send_json({
            "type": "chat_history",
            "data": {"messages": [
                {
                    "id": m.id, "poste_id": m.poste_id, "expediteur": m.expediteur,
                    "operateur_id": m.operateur_id, "message": m.message,
                    "date_envoi": m.date_envoi.isoformat(), "lu": m.lu,
                    "piece_jointe_nom": m.piece_jointe_nom,
                    "piece_jointe_taille_octets": m.piece_jointe_taille_octets,
                    "piece_jointe_content_type": m.piece_jointe_content_type,
                }
                for m in chat_historique
            ]}
        })

        # Code de secours encore valide (déverrouillage admin local hors-ligne,
        # voir PosteService.generer_code_secours) : poussé à chaque (re)connexion
        # pour que le client le mette en cache avant une éventuelle coupure réseau.
        if poste.code_secours_hash and poste.code_secours_expire_le and poste.code_secours_expire_le > datetime.utcnow():
            await websocket.send_json({
                "type": "code_secours",
                "data": {
                    "hash": poste.code_secours_hash,
                    "expire_le": poste.code_secours_expire_le.isoformat(),
                },
            })

        try:
            while True:
                raw = await websocket.receive_json()
                msg_type = raw.get("type")
                data = raw.get("data") or {}

                if msg_type == "heartbeat":
                    await run_in_threadpool(
                        PosteService.heartbeat, db, poste_id,
                        data.get("version_client"), data.get("ip"), data.get("mac_adresse"),
                    )
                    continue

                handler = HANDLERS.get(msg_type)
                if not handler:
                    await websocket.send_json({"type": "error", "data": {"message": f"type de message inconnu: {msg_type}"}})
                    continue

                response = await run_in_threadpool(handler, db, poste_id, data)
                await websocket.send_json(response)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"Erreur WS poste {poste_id}: {e}")
        finally:
            manager.disconnect(poste_id)
            offline_poste = db.query(Poste).get(poste_id)
            if offline_poste:
                offline_poste.est_en_ligne = False
                db.commit()
                manager.broadcast_to_admins_threadsafe("poste_updated", _serialize_poste_for_admin(offline_poste))
    finally:
        db.close()
