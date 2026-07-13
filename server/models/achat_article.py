from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
import enum


class StatutCommande(str, enum.Enum):
    """Suivi d'une commande d'article : de l'achat à la remise en main propre.
    Les ventes au comptoir sont 'recuperee' d'office ; les commandes passées depuis
    le portail WiFi démarrent 'a_preparer'."""
    A_PREPARER = "a_preparer"
    PRETE = "prete"
    RECUPEREE = "recuperee"
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class AchatArticle(Base):
    __tablename__ = "achats_articles"

    id = Column(Integer, primary_key=True, index=True)

    # Article acheté
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    article = relationship("Article")

    # Qui achète ?
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", foreign_keys=[user_id])

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")

    # Paiement associé (si paiement direct)
    paiement_id = Column(Integer, ForeignKey("paiements.id"), nullable=True)
    paiement = relationship("Paiement")
    
    
    # Opérateur qui a réalisé la vente
    operateur_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operateur = relationship("User", foreign_keys=[operateur_id])

    # Prix final (copié depuis Article.prix)
    prix = Column(Float, nullable=False)

    statut_commande = Column(String, default=StatutCommande.RECUPEREE.value)

    # Date
    date_achat = Column(DateTime, default=datetime.utcnow)
