from sqlalchemy.orm import Session
from datetime import datetime

from models.systemSetting import SystemSetting
from server.services.historique_service import HistoriqueService
from server.services.notification_service import NotificationService
from models.notification import TypeNotification


class SystemSettingsService:

    # ---------------------------------------------------------
    # 1. CRÉER UN PARAMÈTRE
    # ---------------------------------------------------------
    @staticmethod
    def creer_parametre(
        db: Session,
        cle: str,
        categorie: str,
        valeur,
        description: str | None = None
    ):
        # Vérifier unicité
        if db.query(SystemSetting).filter_by(cle=cle).first():
            raise ValueError(f"Le paramètre '{cle}' existe déjà")

        setting = SystemSetting(
            cle=cle,
            categorie=categorie,
            valeur=valeur,
            description=description,
            date_modification=datetime.utcnow()
        )

        db.add(setting)
        db.commit()
        db.refresh(setting)

        HistoriqueService.log(
            db=db,
            type_evenement="system_setting_create",
            description=f"Création du paramètre système '{cle}'",
            details={"categorie": categorie, "valeur": valeur}
        )

        return setting

    # ---------------------------------------------------------
    # 2. METTRE À JOUR UN PARAMÈTRE
    # ---------------------------------------------------------
    @staticmethod
    def update_parametre(
        db: Session,
        cle: str,
        nouvelle_valeur,
        description: str | None = None,
        notifier: bool = False
    ):
        setting = db.query(SystemSetting).filter_by(cle=cle).first()
        if not setting:
            raise ValueError(f"Paramètre '{cle}' introuvable")

        ancienne_valeur = setting.valeur

        setting.valeur = nouvelle_valeur
        setting.date_modification = datetime.utcnow()

        if description:
            setting.description = description

        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="system_setting_update",
            description=f"Modification du paramètre '{cle}'",
            details={
                "ancienne_valeur": ancienne_valeur,
                "nouvelle_valeur": nouvelle_valeur
            }
        )

        # Notification optionnelle (ex : changement prix impression)
        if notifier:
            NotificationService.send_system(
                db=db,
                titre=f"Paramètre modifié : {cle}",
                message=f"La valeur du paramètre '{cle}' a été mise à jour.",
                details={"nouvelle_valeur": nouvelle_valeur}
            )

        return setting

    # ---------------------------------------------------------
    # 3. RÉCUPÉRER UN PARAMÈTRE PAR CLÉ
    # ---------------------------------------------------------
    @staticmethod
    def get_parametre(db: Session, cle: str):
        setting = db.query(SystemSetting).filter_by(cle=cle).first()
        if not setting:
            raise ValueError(f"Paramètre '{cle}' introuvable")
        return setting

    # ---------------------------------------------------------
    # 4. RÉCUPÉRER LA VALEUR D’UN PARAMÈTRE
    # ---------------------------------------------------------
    @staticmethod
    def get_valeur(db: Session, cle: str):
        setting = SystemSettingsService.get_parametre(db, cle)
        return setting.valeur

    # ---------------------------------------------------------
    # 5. RÉCUPÉRER TOUS LES PARAMÈTRES D’UNE CATÉGORIE
    # ---------------------------------------------------------
    @staticmethod
    def get_par_categorie(db: Session, categorie: str):
        return (
            db.query(SystemSetting)
            .filter(SystemSetting.categorie == categorie)
            .order_by(SystemSetting.cle.asc())
            .all()
        )

    # ---------------------------------------------------------
    # 6. SUPPRIMER UN PARAMÈTRE
    # ---------------------------------------------------------
    @staticmethod
    def supprimer_parametre(db: Session, cle: str):
        setting = db.query(SystemSetting).filter_by(cle=cle).first()
        if not setting:
            raise ValueError(f"Paramètre '{cle}' introuvable")

        db.delete(setting)
        db.commit()

        HistoriqueService.log(
            db=db,
            type_evenement="system_setting_delete",
            description=f"Suppression du paramètre '{cle}'"
        )

        return True

    # ---------------------------------------------------------
    # 7. INITIALISER DES PARAMÈTRES PAR DÉFAUT (OPTIONNEL)
    # ---------------------------------------------------------
    @staticmethod
    def initialiser_defaults(db: Session, defaults: dict[str,any]=  {
                                 "impression.prix_nb": {"categorie": "impression", "valeur": 0.10},
                                "impression.prix_couleur": {"categorie": "impression", "valeur": 0.25},
                                "reseau.timeout_heartbeat": {"categorie": "reseau", "valeur": 30},
                                                                    }
                             ):
        """
        defaults = {
            "impression.prix_nb": {"categorie": "impression", "valeur": 0.10},
            "impression.prix_couleur": {"categorie": "impression", "valeur": 0.25},
            "reseau.timeout_heartbeat": {"categorie": "reseau", "valeur": 30},
        }
        """
        for cle, data in defaults.items():
            if not db.query(SystemSetting).filter_by(cle=cle).first():
                SystemSettingsService.creer_parametre(
                    db=db,
                    cle=cle,
                    categorie=data["categorie"],
                    valeur=data["valeur"],
                    description=data.get("description")
                )
