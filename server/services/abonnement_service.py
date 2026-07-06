from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.abonnement import Abonnement, is_valide_abonnement
from models.achat import Achat
from models.offre import Offre, OffreTemps, OffreData, OffreIllimite, UniteDuree, is_valide_offre
from models.user import User
from models.paiement import TypePaiement
from models.notification import TypeNotification
from models.historique import TypeEvenement

from services.paiement_service import PaiementService
from services.historique_service import HistoriqueService
from services.notification_service import NotificationService
from services.promotion_service import PromotionService


class AbonnementService:

    # ---------------------------------------------------------
    # CALCUL DE LA DATE DE FIN SELON LA DURÉE DE L'OFFRE
    # ---------------------------------------------------------
    @staticmethod
    def _calculer_date_fin(offre: Offre):
        if not offre.unite_duree or not offre.valeur_duree:
            return None

        if offre.unite_duree == UniteDuree.MINUTE:
            return datetime.utcnow() + timedelta(minutes=offre.valeur_duree)
        if offre.unite_duree == UniteDuree.HEURE:
            return datetime.utcnow() + timedelta(hours=offre.valeur_duree)
        if offre.unite_duree == UniteDuree.JOUR:
            return datetime.utcnow() + timedelta(days=offre.valeur_duree)
        if offre.unite_duree == UniteDuree.HEBDO:
            return datetime.utcnow() + timedelta(weeks=offre.valeur_duree)
        if offre.unite_duree == UniteDuree.MOIS:
            return datetime.utcnow() + timedelta(days=30 * offre.valeur_duree)
        if offre.unite_duree == UniteDuree.ANNEE:
            return datetime.utcnow() + timedelta(days=365 * offre.valeur_duree)

        return None

    # ---------------------------------------------------------
    # 1. SOUSCRIRE À UNE OFFRE (achat + abonnement)
    # ---------------------------------------------------------
    @staticmethod
    def souscrire(
        db: Session,
        user_id: int,
        offre_id: int,
        operateur_id: int | None = None,
        type_paiement: TypePaiement | None = None,
        utiliser_solde: bool = False,
        code_promo: str | None = None
    ):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")

        valide = is_valide_offre(offre)
        if not valide["valide"]:
            raise ValueError(valide["detail"])

        montant, _promo = PromotionService.appliquer(db, offre.prix, offre_id=offre_id, code=code_promo, user_id=user_id)

        if utiliser_solde:
            PaiementService.payer_via_solde(db, user_id, montant)
        else:
            PaiementService.creer_paiement(
                db=db,
                montant=montant,
                type_paiement=type_paiement,
                user_id=user_id,
                operateur_id=operateur_id
            )

        return AbonnementService._activer(db=db, user=user, offre=offre, operateur_id=operateur_id, montant=montant)

    # ---------------------------------------------------------
    # 1bis. ACTIVER UN ABONNEMENT APRÈS UN PAIEMENT DÉJÀ CONFIRMÉ AILLEURS
    # (ex: webhook d'une passerelle de paiement en ligne — voir paiement_service.py)
    # ---------------------------------------------------------
    @staticmethod
    def activer_apres_paiement(db: Session, user_id: int, offre_id: int, montant: float | None = None):
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        offre = db.query(Offre).get(offre_id)
        if not offre:
            raise ValueError("Offre introuvable")

        return AbonnementService._activer(db=db, user=user, offre=offre, montant=montant)

    @staticmethod
    def _activer(db: Session, user: User, offre: Offre, operateur_id: int | None = None, montant: float | None = None):
        date_fin = AbonnementService._calculer_date_fin(offre)
        montant_final = montant if montant is not None else offre.prix

        achat = Achat(
            user_id=user.id,
            operateur_id=operateur_id,
            offre_id=offre.id,
            prix_paye=montant_final,
            date_expiration=date_fin,
            est_actif=True,
            est_consomme=False
        )
        db.add(achat)
        db.commit()
        db.refresh(achat)

        minutes_par_jour = offre.duree_minutes if isinstance(offre, OffreTemps) else None
        data_totale_mo = offre.quota_mo if isinstance(offre, OffreData) else None
        illimite = isinstance(offre, OffreIllimite)

        abonnement = Abonnement(
            user_id=user.id,
            achat_id=achat.id,
            offre_id=offre.id,
            date_fin=date_fin,
            est_actif=True,
            minutes_par_jour=minutes_par_jour,
            minutes_restantes_aujourdhui=minutes_par_jour,
            data_totale_mo=data_totale_mo,
            data_restante_mo=data_totale_mo,
            illimite=illimite
        )
        db.add(abonnement)
        db.commit()
        db.refresh(abonnement)

        user.current_abonnement_id = abonnement.id
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement=TypeEvenement.ABONNEMENT_ACTIVATION,
            description=f"Souscription à l'offre {offre.nom} pour {user.username}",
            user_id=user.id,
            details={"offre": offre.nom, "prix": montant_final}
        )

        NotificationService.send_to_user(
            db=db,
            user_id=user.id,
            titre="Abonnement activé",
            message=f"Votre abonnement '{offre.nom}' est maintenant actif.",
            type_notification=TypeNotification.ABONNEMENT
        )

        return abonnement

    # ---------------------------------------------------------
    # 2. SUSPENDRE / RÉACTIVER
    # ---------------------------------------------------------
    @staticmethod
    def set_suspendu(db: Session, abonnement_id: int, suspendu: bool):
        abonnement = db.query(Abonnement).get(abonnement_id)
        if not abonnement:
            raise ValueError("Abonnement introuvable")

        abonnement.est_suspendu = suspendu
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement=TypeEvenement.ABONNEMENT_ACTIVATION if not suspendu else TypeEvenement.ABONNEMENT_EXPIRATION,
            description=f"Abonnement {abonnement.id} {'suspendu' if suspendu else 'réactivé'}",
            user_id=abonnement.user_id
        )

        if abonnement.user_id:
            NotificationService.send_to_user(
                db=db,
                user_id=abonnement.user_id,
                titre="Abonnement suspendu" if suspendu else "Abonnement réactivé",
                message="Votre abonnement a été suspendu." if suspendu else "Votre abonnement a été réactivé.",
                type_notification=TypeNotification.ABONNEMENT
            )

        return abonnement

    # ---------------------------------------------------------
    # 3. TERMINER UN ABONNEMENT
    # ---------------------------------------------------------
    @staticmethod
    def terminer(db: Session, abonnement_id: int):
        abonnement = db.query(Abonnement).get(abonnement_id)
        if not abonnement:
            raise ValueError("Abonnement introuvable")

        abonnement.est_actif = False
        db.commit()

        user = db.query(User).get(abonnement.user_id) if abonnement.user_id else None
        if user and user.current_abonnement_id == abonnement.id:
            user.current_abonnement_id = None
            db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement=TypeEvenement.ABONNEMENT_EXPIRATION,
            description=f"Abonnement {abonnement.id} terminé",
            user_id=abonnement.user_id
        )

        return abonnement

    # ---------------------------------------------------------
    # 4. CONSOMMATION
    # ---------------------------------------------------------
    @staticmethod
    def consommer(db: Session, abonnement_id: int, minutes: int = 0, data_mo: float = 0):
        abonnement = db.query(Abonnement).get(abonnement_id)
        if not abonnement:
            raise ValueError("Abonnement introuvable")

        if not abonnement.illimite:
            if abonnement.minutes_restantes_aujourdhui is not None:
                abonnement.minutes_restantes_aujourdhui = max(0, abonnement.minutes_restantes_aujourdhui - minutes)
            if abonnement.data_restante_mo is not None:
                abonnement.data_restante_mo = max(0, abonnement.data_restante_mo - data_mo)

        db.commit()
        db.refresh(abonnement)
        return abonnement

    # ---------------------------------------------------------
    # 5. CONSULTATION
    # ---------------------------------------------------------
    @staticmethod
    def get_by_id(db: Session, abonnement_id: int):
        abonnement = db.query(Abonnement).get(abonnement_id)
        if not abonnement:
            raise ValueError("Abonnement introuvable")
        return abonnement

    @staticmethod
    def get_by_user(db: Session, user_id: int):
        return (
            db.query(Abonnement)
            .filter(Abonnement.user_id == user_id)
            .order_by(Abonnement.date_debut.desc())
            .all()
        )

    @staticmethod
    def verifier_validite(db: Session, abonnement_id: int):
        abonnement = AbonnementService.get_by_id(db, abonnement_id)
        return is_valide_abonnement(abonnement)
