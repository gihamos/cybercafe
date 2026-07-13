from sqlalchemy.orm import Session
from datetime import datetime

from models.impression import (
    Impression,
    StatutImpression,
    TypeImpression,
    OrigineImpression
)
from models.paiement import TypePaiement
from services.paiement_service import PaiementService
from services.notification_service import NotificationService
from services.historique_service import HistoriqueService
from models.notification import TypeNotification


class ImpressionService:

    # ---------------------------------------------------------
    # 1. CRÉER UNE DEMANDE D’IMPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def creer_impression(
        db: Session,
        origine: OrigineImpression,
        fichier_nom: str,
        fichier_path: str,
        pages_liste: list[int],
        type_impression: TypeImpression,
        recto_verso: bool,
        prix_par_page: float,
        user_id: int | None = None,
        ticket_id: int | None = None,
        poste_id: int | None = None,
        achat_id: int | None = None,
        operateur_id: int | None = None,
        details: dict | None = None
    ):
        if prix_par_page <= 0:
            raise ValueError("Prix par page invalide")

        pages_total = len(pages_liste)

        impression = Impression(
            origine=origine,
            user_id=user_id,
            ticket_id=ticket_id,
            poste_id=poste_id,
            achat_id=achat_id,
            operateur_id=operateur_id,
            fichier_nom=fichier_nom,
            fichier_path=fichier_path,
            fichier_type=fichier_nom.split(".")[-1].lower(),
            pages_liste=pages_liste,
            pages_total=pages_total,
            selection_pages=",".join(map(str, pages_liste)),
            recto_verso=recto_verso,
            type_impression=type_impression,
            prix_par_page=prix_par_page,
            prix_total=pages_total * prix_par_page,
            statut=StatutImpression.EN_ATTENTE,
            details=details,
            date_impression=datetime.utcnow()
        )

        db.add(impression)
        db.commit()
        db.refresh(impression)

        HistoriqueService.log(
            db=db,
            type_evenement="impression_create",
            description=f"Demande d'impression créée ({pages_total} pages)",
            user_id=user_id,
            ticket_id=ticket_id,
            poste_id=poste_id,
            details={"prix_total": impression.prix_total}
        )

        return impression

    # ---------------------------------------------------------
    # 2. PAYER L’IMPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def payer_impression(
        db: Session,
        impression_id: int,
        utiliser_solde: bool = False,
        type_paiement: TypePaiement | None = None
    ):
        impression = db.query(Impression).get(impression_id)
        if not impression:
            raise ValueError("Impression introuvable")

        montant = impression.prix_total

        if utiliser_solde:
            if not impression.user_id:
                raise ValueError("Le paiement via solde nécessite un utilisateur")
            PaiementService.payer_via_solde(db, impression.user_id, montant)
        else:
            paiement = PaiementService.creer_paiement(
                db=db,
                montant=montant,
                type_paiement=type_paiement,
                user_id=impression.user_id,
                ticket_id=impression.ticket_id
            )
            impression.paiement_id = paiement.id

        impression.paye = True
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="impression_pay",
            description=f"Paiement impression ({montant}€)",
            user_id=impression.user_id,
            ticket_id=impression.ticket_id,
            details={"impression_id": impression.id}
        )

        return impression

    # ---------------------------------------------------------
    # 3. CHANGER LE STATUT
    # ---------------------------------------------------------
    @staticmethod
    def set_statut(db: Session, impression_id: int, statut: StatutImpression, message_erreur: str | None = None):
        impression = db.query(Impression).get(impression_id)
        if not impression:
            raise ValueError("Impression introuvable")

        impression.statut = statut
        impression.message_erreur = message_erreur
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="impression_status",
            description=f"Statut impression → {statut}",
            user_id=impression.user_id,
            ticket_id=impression.ticket_id,
            poste_id=impression.poste_id,
            details={"erreur": message_erreur}
        )

        # Notification utilisateur
        if impression.user_id:
            if statut == StatutImpression.SUCCES:
                NotificationService.send_to_user(
                    db=db,
                    user_id=impression.user_id,
                    titre="Impression terminée",
                    message=f"Votre impression '{impression.fichier_nom}' est prête.",
                    type_notification=TypeNotification.IMPRESSION
                )
            elif statut == StatutImpression.ECHEC:
                NotificationService.send_to_user(
                    db=db,
                    user_id=impression.user_id,
                    titre="Erreur d'impression",
                    message=f"L'impression a échoué : {message_erreur}",
                    type_notification=TypeNotification.IMPRESSION
                )

        return impression

    # ---------------------------------------------------------
    # 4. ANNULER UNE IMPRESSION
    # ---------------------------------------------------------
    @staticmethod
    def annuler_impression(db: Session, impression_id: int):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.ANNULEE
        )

    # ---------------------------------------------------------
    # 5. RÉCUPÉRER LES IMPRESSIONS (filtres)
    # ---------------------------------------------------------
    @staticmethod
    def rechercher_impressions(
        db: Session,
        user_id: int | None = None,
        ticket_id: int | None = None,
        poste_id: int | None = None,
        statut: StatutImpression | None = None,
        origine: OrigineImpression | None = None
    ):
        query = db.query(Impression)

        if user_id:
            query = query.filter(Impression.user_id == user_id)

        if ticket_id:
            query = query.filter(Impression.ticket_id == ticket_id)

        if poste_id:
            query = query.filter(Impression.poste_id == poste_id)

        if statut:
            query = query.filter(Impression.statut == statut)

        if origine:
            query = query.filter(Impression.origine == origine)

        return query.order_by(Impression.date_impression.desc()).all()

    # ---------------------------------------------------------
    # 6. MARQUER COMME EN COURS
    # ---------------------------------------------------------
    @staticmethod
    def demarrer_impression(db: Session, impression_id: int):
        impression = db.query(Impression).get(impression_id)
        if impression and not impression.paye:
            raise ValueError("Impression non réglée : encaissez le paiement avant de la lancer")
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.EN_COURS
        )

    # ---------------------------------------------------------
    # 7. MARQUER COMME RÉUSSIE
    # ---------------------------------------------------------
    @staticmethod
    def terminer_impression(db: Session, impression_id: int):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.SUCCES
        )

    # ---------------------------------------------------------
    # 8. MARQUER COMME ÉCHOUÉE
    # ---------------------------------------------------------
    @staticmethod
    def erreur_impression(db: Session, impression_id: int, message: str):
        return ImpressionService.set_statut(
            db=db,
            impression_id=impression_id,
            statut=StatutImpression.ECHEC,
            message_erreur=message
        )

    # ---------------------------------------------------------
    # 9. SERVEUR D'IMPRESSION — dispatch réel vers la passerelle configurée
    # (voir services/print_gateway/), appelé périodiquement par le worker de fond
    # (config/background_tasks.py). Les boutons manuels de l'admin (Lancer, Encaisser,
    # Annuler...) restent utilisables en parallèle : le worker ne fait que dispatcher
    # les jobs réglés et faire avancer leur statut réel, sans jamais imposer d'action.
    # ---------------------------------------------------------
    @staticmethod
    def traiter_file_attente(db: Session) -> int:
        """Envoie à la vraie imprimante toute demande réglée dont le document est
        disponible dans le stockage serveur. Retourne le nombre de jobs dispatchés.

        Ne concerne PAS les impressions d'origine POSTE : le kiosque imprime déjà en
        local sur son propre spouleur (voir client/ui/print_dialog.py) et facture la
        demande directement en SUCCES — ces enregistrements ne repassent jamais par
        EN_ATTENTE et sont donc naturellement ignorés ici."""
        from models.fichier_stocke import FichierStocke
        from params import PRINT_GATEWAY, PRINT_DEFAULT_PRINTER
        from services.print_gateway import get_print_gateway
        from services.storage_provider import get_provider

        candidats = (
            db.query(Impression)
            .filter(Impression.statut == StatutImpression.EN_ATTENTE, Impression.paye == True)
            .all()
        )
        candidats = [i for i in candidats if (i.details or {}).get("fichier_stocke_id")]
        if not candidats:
            return 0

        gateway = get_print_gateway(PRINT_GATEWAY)
        nb = 0
        for impression in candidats:
            try:
                fichier = db.query(FichierStocke).get(impression.details["fichier_stocke_id"])
                if not fichier:
                    raise ValueError("Document introuvable dans l'espace de stockage")
                provider = get_provider(fichier.provider)
                contenu = provider.download(fichier.cle_stockage).read()
                resultat = gateway.imprimer(
                    contenu=contenu,
                    nom_fichier=impression.fichier_nom,
                    copies=1,
                    recto_verso=impression.recto_verso,
                    couleur=impression.type_impression == TypeImpression.COULEUR,
                    imprimante=PRINT_DEFAULT_PRINTER or None,
                )
            except Exception as e:
                ImpressionService.erreur_impression(db, impression.id, str(e))
                continue

            impression.details = {**(impression.details or {}), "print_job_id": resultat.job_id, "print_gateway": gateway.nom}
            db.commit()

            if resultat.statut == "erreur":
                ImpressionService.erreur_impression(db, impression.id, resultat.message or "Échec d'impression")
            elif resultat.statut == "termine":
                ImpressionService.set_statut(db, impression.id, StatutImpression.SUCCES)
            else:
                ImpressionService.set_statut(db, impression.id, StatutImpression.EN_COURS)
            nb += 1

        return nb

    @staticmethod
    def verifier_jobs_en_cours(db: Session) -> int:
        """Interroge la passerelle d'impression pour les jobs déjà envoyés (statut
        EN_COURS), fait avancer leur statut réel. Retourne le nombre mis à jour."""
        from params import PRINT_GATEWAY
        from services.print_gateway import get_print_gateway

        candidats = (
            db.query(Impression)
            .filter(Impression.statut == StatutImpression.EN_COURS)
            .all()
        )
        if not candidats:
            return 0

        gateway = get_print_gateway(PRINT_GATEWAY)
        nb = 0
        for impression in candidats:
            job_id = (impression.details or {}).get("print_job_id")
            if not job_id:
                continue
            try:
                resultat = gateway.get_statut(job_id)
            except Exception as e:
                ImpressionService.erreur_impression(db, impression.id, str(e))
                nb += 1
                continue

            if resultat.statut == "termine":
                ImpressionService.set_statut(db, impression.id, StatutImpression.SUCCES)
                nb += 1
            elif resultat.statut == "erreur":
                ImpressionService.erreur_impression(db, impression.id, resultat.message or "Échec d'impression")
                nb += 1

        return nb
