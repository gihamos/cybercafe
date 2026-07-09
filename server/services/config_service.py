from sqlalchemy.orm import Session

from services.system_setting_service import SystemSettingsService
from services.historique_service import HistoriqueService

# Clés de configuration générale du cybercafé, avec leur valeur par défaut. Stockées
# dans la table générique system_settings (voir system_setting_service.py) sous la
# catégorie "cybercafe" ou "chat" — ce service n'ajoute qu'une façade pratique pour
# les lire/écrire toutes ensemble depuis le panneau d'administration.
DEFAULTS: dict[str, tuple[str, object]] = {
    "cybercafe.nom": ("cybercafe", "Cybercafé"),
    "cybercafe.logo": ("cybercafe", None),
    "cybercafe.adresse": ("cybercafe", None),
    "cybercafe.siret": ("cybercafe", None),
    "cybercafe.telephone": ("cybercafe", None),
    "cybercafe.email": ("cybercafe", None),
    "cybercafe.devise": ("cybercafe", "EUR"),
    "cybercafe.pied_recu": ("cybercafe", "Merci de votre visite !"),
    "chat.taille_max_fichier_mo": ("chat", 5),
}


class ConfigService:

    @staticmethod
    def get_config(db: Session) -> dict:
        resultat = {}
        for cle, (_categorie, defaut) in DEFAULTS.items():
            try:
                resultat[cle] = SystemSettingsService.get_valeur(db, cle)
            except ValueError:
                resultat[cle] = defaut
        return resultat

    @staticmethod
    def update_config(db: Session, data: dict) -> dict:
        for cle, valeur in data.items():
            if cle not in DEFAULTS:
                continue
            categorie, _defaut = DEFAULTS[cle]
            try:
                SystemSettingsService.update_parametre(db, cle, valeur)
            except ValueError:
                SystemSettingsService.creer_parametre(db, cle=cle, categorie=categorie, valeur=valeur)

        HistoriqueService.log(
            db=db, type_evenement="config_update",
            description="Mise à jour de la configuration du cybercafé", details=data
        )
        return ConfigService.get_config(db)
