from sqlalchemy.orm import Session
from datetime import datetime

from models.paiement import Paiement, TypePaiement, StatutPaiement
from models.user import User
from models.ticket import Ticket
from models.recharge_solde import RechargeSolde

from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from services.payment_gateway import get_gateway
from services.in_person_gateway import get_in_person_gateway
from services.promotion_service import PromotionService
from models.notification import TypeNotification


class PaiementService:

    # ---------------------------------------------------------
    # CRÉER UN PAIEMENT (générique)
    # ---------------------------------------------------------
    @staticmethod
    def creer_paiement(
        db: Session,
        montant: float,
        type_paiement: TypePaiement,
        user_id: int | None = None,
        ticket_id: int | None = None,
        operateur_id: int | None = None,
        statut: str = "succes"
    ):
        if montant <= 0:
            raise ValueError("Montant invalide")

        paiement = Paiement(
            montant=montant,
            type_paiement=type_paiement,
            user_id=user_id,
            ticket_id=ticket_id,
            operateur_id=operateur_id,
            statut=statut,
            date_paiement=datetime.utcnow()
        )

        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        HistoriqueService.log(
            db=db,
            type_evenement="paiement",
            description=f"Paiement de {montant}€ ({type_paiement})",
            user_id=user_id,
            ticket_id=ticket_id,
            details={"statut": statut}
        )

        return paiement

    # ---------------------------------------------------------
    # ENCAISSEMENT EN CAISSE (comptoir) — valide via l'API du fournisseur pour
    # carte/mobile money avant d'enregistrer le paiement comme réussi ; espèces/
    # virement/gratuit sont enregistrés directement (confirmation manuelle par
    # l'opérateur, aucune API de validation synchrone pour ces moyens).
    # ---------------------------------------------------------
    @staticmethod
    def encaisser_caisse(
        db: Session,
        montant: float,
        type_paiement: TypePaiement,
        operateur_id: int,
        user_id: int | None = None,
        ticket_id: int | None = None,
        metadata: dict | None = None,
        crediter_solde: bool = False,
        code_promo: str | None = None,
    ) -> Paiement:
        if montant <= 0:
            raise ValueError("Montant invalide")
        if user_id is None and ticket_id is None:
            raise ValueError("Un encaissement doit être rattaché à un client ou un ticket")
        if crediter_solde and user_id is None:
            raise ValueError("Une recharge de solde doit être rattachée à un client")

        promos_appliquees = []
        if code_promo:
            montant, promos_appliquees = PromotionService.appliquer(db, montant, code=code_promo, user_id=user_id)

        valeur_type = type_paiement.value if hasattr(type_paiement, "value") else type_paiement
        reference = None
        details = None

        gateway = get_in_person_gateway(valeur_type)
        if gateway:
            reference_client = f"caisse-{operateur_id}-{int(datetime.utcnow().timestamp())}"
            try:
                resultat = gateway.valider_paiement(montant, "EUR", reference_client, metadata or {})
            except Exception as e:
                raise ValueError(f"Fournisseur {valeur_type} injoignable : {e}")
            if not resultat.succes:
                raise ValueError(f"Paiement {valeur_type} refusé par le fournisseur (statut : {resultat.statut})")
            reference = resultat.reference
            details = {"gateway": gateway.nom, "statut_fournisseur": resultat.statut}

        paiement = Paiement(
            montant=montant,
            type_paiement=type_paiement,
            user_id=user_id,
            ticket_id=ticket_id,
            operateur_id=operateur_id,
            statut=StatutPaiement.SUCCES,
            reference=reference,
            details=details,
            date_paiement=datetime.utcnow()
        )
        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        PromotionService.lier_paiement(db, paiement.id, promos_appliquees)

        if crediter_solde:
            user = db.query(User).get(user_id)
            recharge = RechargeSolde(user_id=user_id, paiement_id=paiement.id, montant=montant)
            db.add(recharge)
            user.solde_euros += montant
            db.commit()

            NotificationService.send_to_user(
                db=db,
                user_id=user_id,
                titre="Recharge effectuée",
                message=f"Votre solde a été crédité de {montant}€.",
                type_notification=TypeNotification.PAIEMENT
            )

        HistoriqueService.log(
            db=db,
            type_evenement="paiement",
            description=(
                f"Recharge de solde de {montant}€ ({valeur_type}) en caisse" if crediter_solde
                else f"Encaissement de {montant}€ ({valeur_type}) en caisse"
            ),
            user_id=user_id,
            operateur_id=operateur_id,
            ticket_id=ticket_id,
            details={"reference": reference}
        )

        return paiement

    # ---------------------------------------------------------
    # PAIEMENT POUR UN USER (solde NON utilisé)
    # ---------------------------------------------------------
    @staticmethod
    def payer_user(
        db: Session,
        user_id: int,
        montant: float,
        type_paiement: TypePaiement
    ):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        paiement = PaiementService.creer_paiement(
            db=db,
            montant=montant,
            type_paiement=type_paiement,
            user_id=user_id
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            titre="Paiement effectué",
            message=f"Un paiement de {montant}€ a été enregistré.",
            type_notification=TypeNotification.PAIEMENT
        )

        return paiement

    # ---------------------------------------------------------
    # PAIEMENT POUR UN TICKET (toujours direct)
    # ---------------------------------------------------------
    @staticmethod
    def payer_ticket(
        db: Session,
        ticket_id: int,
        montant: float,
        type_paiement: TypePaiement
    ):
        ticket = db.query(Ticket).get(ticket_id)
        if not ticket:
            raise ValueError("Ticket introuvable")

        paiement = PaiementService.creer_paiement(
            db=db,
            montant=montant,
            type_paiement=type_paiement,
            ticket_id=ticket_id
        )

        return paiement

    # ---------------------------------------------------------
    # PAIEMENT VIA SOLDE UTILISATEUR
    # ---------------------------------------------------------
    @staticmethod
    def payer_via_solde(db: Session, user_id: int, montant: float):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if user.solde_euros < montant:
            raise ValueError("Solde insuffisant")

        user.solde_euros -= montant
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement_solde",
            description=f"Paiement via solde de {montant}€",
            user_id=user_id,
            details={"nouveau_solde": user.solde_euros}
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            titre="Paiement via solde",
            message=f"Un montant de {montant}€ a été débité de votre solde.",
            type_notification=TypeNotification.PAIEMENT
        )

        return user.solde_euros

    # ---------------------------------------------------------
    # RECHERCHE / LISTE
    # ---------------------------------------------------------
    @staticmethod
    def rechercher_paiements(
        db: Session,
        user_id: int | None = None,
        ticket_id: int | None = None,
        operateur_id: int | None = None,
        type_paiement: TypePaiement | None = None,
        statut: str | None = None,
        date_apres: datetime | None = None,
        date_avant: datetime | None = None
    ):
        query = db.query(Paiement)

        if user_id:
            query = query.filter(Paiement.user_id == user_id)

        if ticket_id:
            query = query.filter(Paiement.ticket_id == ticket_id)

        if operateur_id:
            query = query.filter(Paiement.operateur_id == operateur_id)

        if type_paiement:
            query = query.filter(Paiement.type_paiement == type_paiement)

        if statut:
            query = query.filter(Paiement.statut == statut)

        if date_apres:
            query = query.filter(Paiement.date_paiement >= date_apres)

        if date_avant:
            query = query.filter(Paiement.date_paiement <= date_avant)

        return query.order_by(Paiement.date_paiement.desc()).all()

    @staticmethod
    def get_by_id(db: Session, paiement_id: int):
        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Paiement introuvable")
        return paiement

    # ---------------------------------------------------------
    # PAIEMENT EN LIGNE (PayPal etc.) — CRÉATION DE COMMANDE
    # ---------------------------------------------------------
    @staticmethod
    def creer_commande_en_ligne(
        db: Session,
        gateway_nom: str,
        intent: str,  # "recharge_solde" | "achat_offre"
        user_id: int,
        montant: float | None = None,
        offre_id: int | None = None,
        devise: str = "EUR"
    ):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        if intent == "recharge_solde":
            if not montant or montant <= 0:
                raise ValueError("Montant invalide")
            description = f"Recharge de solde pour {user.username}"
            montant_final = montant

        elif intent == "achat_offre":
            from models.offre import Offre, is_valide_offre

            if not offre_id:
                raise ValueError("offre_id requis pour un achat d'offre")

            offre = db.query(Offre).get(offre_id)
            if not offre:
                raise ValueError("Offre introuvable")

            valide = is_valide_offre(offre)
            if not valide["valide"]:
                raise ValueError(valide["detail"])

            description = f"Achat de l'offre {offre.nom} pour {user.username}"
            montant_final = offre.prix

        else:
            raise ValueError(f"Intent de paiement inconnu : {intent}")

        paiement = Paiement(
            user_id=user_id,
            montant=montant_final,
            devise=devise,
            type_paiement=TypePaiement.PAYPAL,
            statut=StatutPaiement.EN_ATTENTE,
            details={"intent": intent, "offre_id": offre_id, "gateway": gateway_nom}
        )
        db.add(paiement)
        db.commit()
        db.refresh(paiement)

        gateway = get_gateway(gateway_nom)
        commande = gateway.creer_commande(
            montant=montant_final,
            devise=devise,
            reference=f"paiement-{paiement.id}",
            description=description
        )

        paiement.reference = commande.order_id
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement_en_ligne_cree",
            description=f"Commande {gateway_nom} créée pour {user.username} ({intent})",
            user_id=user_id,
            details={"paiement_id": paiement.id, "order_id": commande.order_id}
        )

        return {
            "paiement_id": paiement.id,
            "order_id": commande.order_id,
            "approval_url": commande.approval_url
        }

    # ---------------------------------------------------------
    # PAIEMENT EN LIGNE — TRAITEMENT DU WEBHOOK DE CONFIRMATION
    # ---------------------------------------------------------
    @staticmethod
    def traiter_webhook_paiement(db: Session, gateway_nom: str, headers: dict, raw_body: bytes):
        gateway = get_gateway(gateway_nom)
        event = gateway.verifier_webhook(headers, raw_body)
        if not event:
            raise ValueError("Signature de webhook invalide")

        event_type = event.get("event_type")
        if event_type not in ("CHECKOUT.ORDER.APPROVED", "PAYMENT.CAPTURE.COMPLETED"):
            return {"ignored": True, "event_type": event_type}

        if event_type == "CHECKOUT.ORDER.APPROVED":
            order_id = event["resource"]["id"]
        else:
            order_id = event["resource"]["supplementary_data"]["related_ids"]["order_id"]

        paiement = db.query(Paiement).filter(Paiement.reference == order_id).first()
        if not paiement:
            raise ValueError(f"Aucun paiement trouvé pour la commande {order_id}")

        # Idempotence : PayPal peut renvoyer le même webhook plusieurs fois
        if paiement.statut == StatutPaiement.SUCCES:
            return {"already_processed": True, "paiement_id": paiement.id}

        # Paiement annulé côté cybercafé : on ne capture pas la commande même si
        # le client a fini par approuver côté fournisseur.
        if paiement.statut == StatutPaiement.ANNULE:
            return {"cancelled": True, "paiement_id": paiement.id}

        commande = gateway.capturer_commande(order_id)
        if commande.statut != "COMPLETED":
            return {"success": False, "statut": commande.statut}

        paiement.statut = StatutPaiement.SUCCES
        db.commit()

        PaiementService._appliquer_intent(db, paiement)

        return {"success": True, "paiement_id": paiement.id}

    @staticmethod
    def _appliquer_intent(db: Session, paiement: Paiement):
        details = paiement.details or {}
        intent = details.get("intent")

        if intent == "recharge_solde":
            user = db.query(User).get(paiement.user_id)
            user.solde_euros += paiement.montant
            db.commit()

            HistoriqueService.log(
                db=db,
                type_evenement="paiement_solde",
                description=f"Recharge en ligne de {paiement.montant}€ pour {user.username}",
                user_id=user.id,
                details={"nouveau_solde": user.solde_euros}
            )
            NotificationService.send_to_user(
                db=db,
                user_id=user.id,
                titre="Recharge confirmée",
                message=f"Votre solde a été crédité de {paiement.montant}€.",
                type_notification=TypeNotification.PAIEMENT
            )

        elif intent == "achat_offre":
            from services.abonnement_service import AbonnementService
            AbonnementService.activer_apres_paiement(
                db=db,
                user_id=paiement.user_id,
                offre_id=details.get("offre_id"),
                montant=paiement.montant
            )

        elif intent == "achat_ticket":
            # Achat de ticket en ligne (portail WiFi) : le ticket a été pré-généré
            # inactif au moment de la commande — le paiement confirmé l'active.
            from models.ticket import Ticket
            ticket = db.query(Ticket).get(paiement.ticket_id)
            if ticket:
                ticket.est_actif = True
                db.commit()
                HistoriqueService.log(
                    db=db,
                    type_evenement="achat",
                    description=f"Ticket {ticket.code} activé après paiement en ligne de {paiement.montant}€",
                    ticket_id=ticket.id,
                    details={"paiement_id": paiement.id}
                )

    # ---------------------------------------------------------
    # CONFIRMATION D'UNE COMMANDE DÉMO (portail — développement/test uniquement)
    # Joue le rôle du retour de redirection d'une vraie passerelle : le porteur du
    # secret par commande (retourné à la création) confirme le paiement.
    # ---------------------------------------------------------
    @staticmethod
    def confirmer_commande_demo(db: Session, paiement_id: int, secret: str):
        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Paiement introuvable")

        details = paiement.details or {}
        if details.get("gateway") != "demo":
            raise ValueError("Ce paiement ne passe pas par la passerelle démo")
        if not secret or details.get("secret") != secret:
            raise ValueError("Secret de commande invalide")
        if paiement.statut == StatutPaiement.SUCCES:
            return paiement
        if paiement.statut != StatutPaiement.EN_ATTENTE:
            raise ValueError("Ce paiement n'est plus en attente")

        paiement.statut = StatutPaiement.SUCCES
        db.commit()

        PaiementService._appliquer_intent(db, paiement)
        return paiement

    # ---------------------------------------------------------
    # ANNULATION / SUPPRESSION D'UN PAIEMENT EN ATTENTE
    # Un paiement en attente n'a jamais été validé par un fournisseur ni crédité
    # nulle part : on peut l'annuler (trace conservée) ou le supprimer (admin)
    # sans contrepartie financière — contrairement au remboursement.
    # ---------------------------------------------------------
    @staticmethod
    def annuler_en_attente(db: Session, paiement_id: int, operateur_id: int | None = None):
        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Paiement introuvable")

        if paiement.statut != StatutPaiement.EN_ATTENTE:
            raise ValueError("Seul un paiement en attente peut être annulé (utiliser le remboursement pour un paiement réussi)")

        paiement.statut = StatutPaiement.ANNULE
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement_annule",
            description=f"Annulation du paiement en attente {paiement_id} ({paiement.montant}€)",
            user_id=paiement.user_id,
            operateur_id=operateur_id,
            ticket_id=paiement.ticket_id
        )

        return paiement

    @staticmethod
    def supprimer_en_attente(db: Session, paiement_id: int, operateur_id: int | None = None):
        from models.paiement_promotion import PaiementPromotion
        from models.achat_article import AchatArticle
        from models.recharge_solde import RechargeSolde as RechargeSoldeModel

        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Paiement introuvable")

        if paiement.statut != StatutPaiement.EN_ATTENTE:
            raise ValueError("Seul un paiement en attente peut être supprimé")

        # Garde-fous comptables : un paiement en attente ne devrait être lié à
        # aucune vente ni recharge — si c'est le cas, on refuse plutôt que de
        # casser la traçabilité.
        if db.query(AchatArticle).filter(AchatArticle.paiement_id == paiement.id).first():
            raise ValueError("Ce paiement est lié à une vente d'article, suppression impossible")
        if db.query(RechargeSoldeModel).filter(RechargeSoldeModel.paiement_id == paiement.id).first():
            raise ValueError("Ce paiement est lié à une recharge de solde, suppression impossible")

        montant, user_id, ticket_id = paiement.montant, paiement.user_id, paiement.ticket_id
        db.query(PaiementPromotion).filter(PaiementPromotion.paiement_id == paiement.id).delete()
        db.delete(paiement)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="paiement_supprime",
            description=f"Suppression du paiement en attente {paiement_id} ({montant}€)",
            user_id=user_id,
            operateur_id=operateur_id,
            ticket_id=ticket_id
        )

    # ---------------------------------------------------------
    # REMBOURSEMENT
    # ---------------------------------------------------------
    @staticmethod
    def rembourser(db: Session, paiement_id: int):
        paiement = db.query(Paiement).get(paiement_id)
        if not paiement:
            raise ValueError("Paiement introuvable")

        if paiement.statut == "annule":
            raise ValueError("Paiement déjà annulé")

        # Carte/mobile money : le remboursement doit repasser par le fournisseur qui a
        # validé le paiement initial, pas juste être acté localement.
        valeur_type = paiement.type_paiement.value if hasattr(paiement.type_paiement, "value") else paiement.type_paiement
        gateway = get_in_person_gateway(valeur_type)
        if gateway and paiement.reference:
            try:
                resultat = gateway.rembourser(paiement.reference, paiement.montant)
            except Exception as e:
                raise ValueError(f"Fournisseur {valeur_type} injoignable pour le remboursement : {e}")
            if not resultat.succes:
                raise ValueError(f"Échec du remboursement auprès du fournisseur (statut : {resultat.statut})")

        paiement.statut = "annule"
        db.commit()

        # Si paiement lié à un user → remboursement dans le solde
        if paiement.user_id:
            user = db.query(User).get(paiement.user_id)
            user.solde_euros += paiement.montant
            db.commit()

            NotificationService.send_to_user(
                db=db,
                user_id=user.id,
                titre="Remboursement effectué",
                message=f"Un remboursement de {paiement.montant}€ a été crédité sur votre solde.",
                type_notification=TypeNotification.PAIEMENT
            )

        HistoriqueService.log(
            db=db,
            type_evenement="remboursement",
            description=f"Remboursement du paiement {paiement_id}",
            user_id=paiement.user_id,
            ticket_id=paiement.ticket_id
        )

        return paiement
