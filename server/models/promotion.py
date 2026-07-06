from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)

    nom = Column(String, nullable=False)
    # NULL = promo automatique (appliquée sans code) ; sinon code à saisir par le client
    code = Column(String, unique=True, nullable=True)

    # Clé du mécanisme d'application (voir services/promotion_mechanisms/) :
    # "pourcentage", "montant_fixe", ou un mécanisme personnalisé enregistré là-bas.
    # Volontairement une String libre (pas un Enum SQL) pour rester extensible sans
    # migration à chaque nouveau mécanisme.
    mecanisme = Column(String, nullable=False, default="pourcentage")

    # Paramètre principal utilisé par la plupart des mécanismes (pourcentage ou
    # montant selon le mécanisme). Les mécanismes personnalisés peuvent l'ignorer
    # et piocher uniquement dans `parametres`.
    valeur = Column(Float, nullable=False)

    # Configuration libre propre à un mécanisme personnalisé (ex: plage horaire
    # pour "happy_hour"). Ignoré par les mécanismes intégrés simples.
    parametres = Column(JSON, nullable=True)

    # NULL = s'applique à toutes les offres/tous les articles (promo boutique entière)
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=True)
    offre = relationship("Offre")
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    article = relationship("Article")

    date_debut = Column(DateTime, default=datetime.utcnow)
    date_fin = Column(DateTime, nullable=True)

    usage_max = Column(Integer, nullable=True)  # NULL = illimité
    usage_count = Column(Integer, default=0)

    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)


def is_valide_promotion(promo: Promotion) -> dict[str, any]:
    """Vérifications génériques (indépendantes du mécanisme) : actif, dates,
    quota d'utilisation. Les conditions propres à un mécanisme (ex: plage
    horaire) sont vérifiées séparément par PromotionMechanism.est_applicable."""

    if not promo.actif:
        return {"valide": False, "detail": "Cette promotion n'est plus active."}

    if promo.date_debut and promo.date_debut > datetime.utcnow():
        return {"valide": False, "detail": "Cette promotion n'a pas encore commencé."}

    if promo.date_fin and promo.date_fin < datetime.utcnow():
        return {"valide": False, "detail": "Cette promotion a expiré."}

    if promo.usage_max is not None and promo.usage_count >= promo.usage_max:
        return {"valide": False, "detail": "Cette promotion a atteint son nombre maximum d'utilisations."}

    return {"valide": True, "detail": "Promotion valide."}
