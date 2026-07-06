from sqlalchemy.orm import Session
from datetime import datetime

from models.session_caisse import SessionCaisse
from models.paiement import Paiement, TypePaiement, StatutPaiement
from services.historique_service import HistoriqueService


class CaisseService:

    # ---------------------------------------------------------
    # 1. OUVRIR UNE CAISSE
    # ---------------------------------------------------------
    @staticmethod
    def ouvrir(db: Session, operateur_id: int, montant_ouverture: float = 0):
        if montant_ouverture < 0:
            raise ValueError("Le montant d'ouverture ne peut pas être négatif")

        existante = db.query(SessionCaisse).filter(
            SessionCaisse.operateur_id == operateur_id,
            SessionCaisse.est_ouverte == True
        ).first()
        if existante:
            raise ValueError("Une caisse est déjà ouverte pour cet opérateur")

        session_caisse = SessionCaisse(
            operateur_id=operateur_id,
            montant_ouverture=montant_ouverture,
            date_ouverture=datetime.utcnow(),
            est_ouverte=True
        )
        db.add(session_caisse)
        db.commit()
        db.refresh(session_caisse)

        HistoriqueService.log(
            db=db,
            type_evenement="caisse_ouverture",
            description=f"Ouverture de caisse ({montant_ouverture}€)",
            user_id=operateur_id
        )

        return session_caisse

    # ---------------------------------------------------------
    # 2. RÉCUPÉRER LA CAISSE OUVERTE D'UN OPÉRATEUR
    # ---------------------------------------------------------
    @staticmethod
    def get_ouverte(db: Session, operateur_id: int):
        return db.query(SessionCaisse).filter(
            SessionCaisse.operateur_id == operateur_id,
            SessionCaisse.est_ouverte == True
        ).first()

    # ---------------------------------------------------------
    # 3. TOTAL DES ENCAISSEMENTS EN ESPÈCES SUR UNE PÉRIODE
    # ---------------------------------------------------------
    @staticmethod
    def _calculer_total_especes(db: Session, operateur_id: int, date_debut: datetime, date_fin: datetime) -> float:
        paiements = db.query(Paiement).filter(
            Paiement.operateur_id == operateur_id,
            Paiement.type_paiement == TypePaiement.ESPECES,
            Paiement.statut == StatutPaiement.SUCCES,
            Paiement.date_paiement >= date_debut,
            Paiement.date_paiement <= date_fin
        ).all()
        return sum(p.montant for p in paiements)

    # ---------------------------------------------------------
    # 4. CLÔTURER UNE CAISSE (rapprochement)
    # ---------------------------------------------------------
    @staticmethod
    def cloturer(db: Session, session_caisse_id: int, montant_cloture_reel: float, notes: str | None = None):
        session_caisse = db.query(SessionCaisse).get(session_caisse_id)
        if not session_caisse:
            raise ValueError("Session de caisse introuvable")
        if not session_caisse.est_ouverte:
            raise ValueError("Cette caisse est déjà clôturée")

        date_fin = datetime.utcnow()
        total_especes = CaisseService._calculer_total_especes(
            db, session_caisse.operateur_id, session_caisse.date_ouverture, date_fin
        )
        montant_theorique = session_caisse.montant_ouverture + total_especes

        session_caisse.montant_cloture_theorique = montant_theorique
        session_caisse.montant_cloture_reel = montant_cloture_reel
        session_caisse.ecart = round(montant_cloture_reel - montant_theorique, 2)
        session_caisse.date_cloture = date_fin
        session_caisse.est_ouverte = False
        session_caisse.notes = notes

        db.commit()
        db.refresh(session_caisse)

        HistoriqueService.log(
            db=db,
            type_evenement="caisse_cloture",
            description=(
                f"Clôture de caisse : théorique {montant_theorique}€, "
                f"réel {montant_cloture_reel}€, écart {session_caisse.ecart}€"
            ),
            user_id=session_caisse.operateur_id,
            details={
                "theorique": montant_theorique,
                "reel": montant_cloture_reel,
                "ecart": session_caisse.ecart
            }
        )

        return session_caisse

    # ---------------------------------------------------------
    # 5. CONSULTATION
    # ---------------------------------------------------------
    @staticmethod
    def lister(db: Session, operateur_id: int | None = None):
        query = db.query(SessionCaisse)
        if operateur_id:
            query = query.filter(SessionCaisse.operateur_id == operateur_id)
        return query.order_by(SessionCaisse.date_ouverture.desc()).all()

    @staticmethod
    def get_by_id(db: Session, session_caisse_id: int):
        session_caisse = db.query(SessionCaisse).get(session_caisse_id)
        if not session_caisse:
            raise ValueError("Session de caisse introuvable")
        return session_caisse
