import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship

from config.database import Base


class StatutVenteCaisse(str, enum.Enum):
    PAYEE = "payee"
    PARTIELLEMENT_REMBOURSEE = "partiellement_remboursee"
    REMBOURSEE = "remboursee"


class TypeLigneVente(str, enum.Enum):
    ARTICLE = "article"
    FORFAIT = "forfait"
    BON = "bon"  # bon de recharge (coupon) vendu en caisse


class VenteCaisse(Base):
    """Ticket de caisse : une vente groupée encaissée au comptoir (articles,
    forfaits, bons...), identifiée par une référence unique imprimée en
    code-barres sur le ticket — c'est elle qu'on scanne pour un remboursement."""

    __tablename__ = "ventes_caisse"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, nullable=False, index=True)

    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operateur = relationship("User", foreign_keys=[operateur_id])

    # NULL = client de passage (le paiement est alors porté par le compte système
    # « client de passage », voir VenteCaisseService)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", foreign_keys=[user_id])

    paiement_id = Column(Integer, ForeignKey("paiements.id"), nullable=True)
    paiement = relationship("Paiement")

    type_paiement = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    montant_rembourse = Column(Float, default=0)
    statut = Column(SqlEnum(StatutVenteCaisse), default=StatutVenteCaisse.PAYEE)

    date_vente = Column(DateTime, default=datetime.utcnow)

    lignes = relationship("LigneVenteCaisse", back_populates="vente", cascade="all, delete-orphan")


class LigneVenteCaisse(Base):
    __tablename__ = "lignes_vente_caisse"

    id = Column(Integer, primary_key=True, index=True)

    vente_id = Column(Integer, ForeignKey("ventes_caisse.id"), nullable=False)
    vente = relationship("VenteCaisse", back_populates="lignes")

    type_ligne = Column(SqlEnum(TypeLigneVente), nullable=False)

    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    article = relationship("Article")
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=True)
    offre = relationship("Offre")
    # ticket généré par la ligne : ticket de connexion (forfait vendu à un client de
    # passage) ou bon de recharge — son code est imprimé sur le ticket de caisse
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")
    # abonnement activé par la ligne (forfait vendu à un client identifié)
    abonnement_id = Column(Integer, ForeignKey("abonnements.id"), nullable=True)

    designation = Column(String, nullable=False)
    prix_unitaire = Column(Float, nullable=False)
    quantite = Column(Integer, nullable=False, default=1)
    quantite_remboursee = Column(Integer, nullable=False, default=0)
