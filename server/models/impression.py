from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean,
    ForeignKey, Enum as SqlEnum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base
import enum


class StatutImpression(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    SUCCES = "succes"
    ECHEC = "echec"
    ANNULEE = "annulee"


class TypeImpression(str, enum.Enum):
    NOIR_BLANC = "noir_blanc"
    COULEUR = "couleur"


class OrigineImpression(str, enum.Enum):
    POSTE = "poste"
    WIFI = "wifi"
    MOBILE = "mobile"
    PORTAIL_WEB = "portail_web"



class Impression(Base):
    __tablename__ = "impressions"

    id = Column(Integer, primary_key=True, index=True)

    # --- Origine ---
    origine = Column(SqlEnum(OrigineImpression), nullable=False)

    # --- Relations ---
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User", foreign_keys=[operateur_id])

    poste_id = Column(Integer, ForeignKey("postes.id"), nullable=True)
    poste = relationship("Poste")

    achat_id = Column(Integer, ForeignKey("achats.id"), nullable=True)
    achat = relationship("Achat")

    paiement_id = Column(Integer, ForeignKey("paiements.id"), nullable=True)
    paiement = relationship("Paiement")

    # --- Fichier ---
    fichier_nom = Column(String, nullable=False)
    fichier_type = Column(String, nullable=True)
    fichier_path = Column(String, nullable=False)

    # --- Sélection de pages ---
    selection_pages = Column(String, nullable=True)  # ex: "1-5,10"
    pages_liste = Column(JSON, nullable=True)        # ex: [1,2,3,4,5,10]
    pages_total = Column(Integer, nullable=False)    # ex: 6

    # --- Paramètres impression ---
    recto_verso = Column(Boolean, default=False)
    type_impression = Column(SqlEnum(TypeImpression), nullable=False)

    # --- Tarification ---
    prix_par_page = Column(Float, nullable=False)
    prix_total = Column(Float, nullable=False)

    # --- Statut ---
    statut = Column(SqlEnum(StatutImpression), default=StatutImpression.EN_ATTENTE)
    message_erreur = Column(String, nullable=True)

    # --- Données techniques ---
    details = Column(JSON, nullable=True)

    # --- Date ---
    date_impression = Column(DateTime, default=datetime.utcnow)
