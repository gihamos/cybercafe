from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Enum as SqlEnum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class TypeEvenement(str, enum.Enum):
    CONNEXION = "connexion"
    DECONNEXION = "deconnexion"
    CHANGEMENT_POSTE = "changement_poste"
    ACHAT = "achat"
    CONSOMMATION = "consommation"
    ABONNEMENT_ACTIVATION = "abonnement_activation"
    ABONNEMENT_EXPIRATION = "abonnement_expiration"
    IMPRESSION = "impression"
    POSTE_BLOQUE = "poste_bloque"
    POSTE_DEBLOQUE = "poste_debloque"
    ERREUR_SYSTEME = "erreur_systeme"
    ACTION_OPERATEUR = "action_operateur"
    NOTIFICATION_USER = "notification_user"
    AUTRE = "autre"

    # Événements utilisés par les services (historique détaillé)
    poste_create = "poste_create"
    poste_update = "poste_update"
    poste_lock = "poste_lock"
    poste_unlock = "poste_unlock"
    poste_occupy = "poste_occupy"
    poste_free = "poste_free"
    poste_command = "poste_command"
    poste_delete = "poste_delete"
    poste_disable_kiosk = "poste_disable_kiosk"
    poste_code_secours = "poste_code_secours"

    app_bloquee_create = "app_bloquee_create"
    app_bloquee_update = "app_bloquee_update"
    app_bloquee_delete = "app_bloquee_delete"

    lecteur_bloque_create = "lecteur_bloque_create"
    lecteur_bloque_update = "lecteur_bloque_update"
    lecteur_bloque_delete = "lecteur_bloque_delete"

    caisse_ouverture = "caisse_ouverture"
    caisse_cloture = "caisse_cloture"

    promotion_create = "promotion_create"
    promotion_update = "promotion_update"
    promotion_delete = "promotion_delete"
    promotion_appliquee = "promotion_appliquee"

    offre_create = "offre_create"
    offre_update = "offre_update"
    offre_status = "offre_status"
    offre_delete = "offre_delete"

    article_create = "article_create"
    article_update = "article_update"
    article_status = "article_status"
    article_delete = "article_delete"
    article_buy = "article_buy"

    bp_profil_update = "bp_profil_update"
    bp_blocage = "bp_blocage"

    impression_create = "impression_create"
    impression_pay = "impression_pay"
    impression_status = "impression_status"

    notification_operateur = "notification_operateur"
    notification_poste = "notification_poste"
    notification_system = "notification_system"
    notification_ticket = "notification_ticket"

    paiement = "paiement"
    paiement_solde = "paiement_solde"
    paiement_en_ligne_cree = "paiement_en_ligne_cree"
    paiement_annule = "paiement_annule"
    paiement_supprime = "paiement_supprime"
    remboursement = "remboursement"

    session_start = "session_start"
    session_end = "session_end"
    session_move = "session_move"

    system_setting_create = "system_setting_create"
    system_setting_update = "system_setting_update"
    system_setting_delete = "system_setting_delete"

    activation_user = "activation_user"
    desactivation_user = "desactivation_user"
    update_date_expiration = "update_date_expiration"
    update_role = "update_role"
    suppression_user = "suppression_user"

    chat_message = "chat_message"
    chat_conversation_conservee = "chat_conversation_conservee"

    stockage_upload = "stockage_upload"
    stockage_delete = "stockage_delete"
    stockage_quota_update = "stockage_quota_update"

    pay_connect_request = "pay_connect_request"
    pay_connect_confirm = "pay_connect_confirm"
    pay_connect_refuse = "pay_connect_refuse"
    pay_connect_solde = "pay_connect_solde"

    user_group_create = "user_group_create"
    user_group_update = "user_group_update"
    user_group_delete = "user_group_delete"

    poste_wol = "poste_wol"

    article_categorie_create = "article_categorie_create"
    article_categorie_update = "article_categorie_update"
    article_categorie_delete = "article_categorie_delete"

    site_regle_create = "site_regle_create"
    site_regle_update = "site_regle_update"
    site_regle_delete = "site_regle_delete"

    ticket_update = "ticket_update"

    article_stock_update = "article_stock_update"

    config_update = "config_update"

    permissions_update = "permissions_update"

    screenshot_capture = "screenshot_capture"
    navigation_ingestion = "navigation_ingestion"


class Historique(Base):
    __tablename__ = "historiques"

    id = Column(Integer, primary_key=True, index=True)

    # Type d'événement
    type_evenement = Column(SqlEnum(TypeEvenement), nullable=False)

    # Description lisible
    description = Column(String, nullable=False)

    # Données supplémentaires (flexible)
    details = Column(JSON, nullable=True)

    # Qui a fait l'action ?
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    operateur = relationship("User", foreign_keys=[operateur_id])
    
    ticket_id=Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket=relationship("Ticket", foreign_keys=[ticket_id])

    # Où ?
    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)
    poste = relationship("Poste")

    # Quand ?
    timestamp = Column(DateTime, default=datetime.utcnow)
