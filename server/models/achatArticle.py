from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
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
    user = relationship("User")

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket = relationship("Ticket")

    # Paiement associé (si paiement direct)
    paiement_id = Column(Integer, ForeignKey("paiements.id"), nullable=True)
    paiement = relationship("Paiement")

    # Prix final (copié depuis Article.prix)
    prix = Column(Float, nullable=False)

    # Date
    date_achat = Column(DateTime, default=datetime.utcnow)
