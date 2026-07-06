from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PromotionContext:
    """Contexte de l'achat en cours, passé à un mécanisme pour qu'il décide s'il
    s'applique et calcule la réduction. Étendre ce contexte (plutôt que la
    signature des méthodes) si un futur mécanisme personnalisé a besoin d'une
    donnée supplémentaire (ex: nombre d'achats précédents du client)."""

    montant: float
    offre_id: int | None = None
    article_id: int | None = None
    user_id: int | None = None
    moment: datetime = None

    def __post_init__(self):
        if self.moment is None:
            self.moment = datetime.utcnow()


class PromotionMechanism(ABC):
    """Interface d'un mécanisme d'application de promotion.

    Une Promotion référence un mécanisme par sa clé (Promotion.mecanisme, ex:
    "pourcentage"). Pour ajouter un mécanisme personnalisé (ex: happy hour, offre
    de bienvenue, "2 achetés = 1 offert"...) : créer une classe ici qui implémente
    ces deux méthodes, puis l'enregistrer dans __init__.py::_MECANISMES — rien
    d'autre à changer côté service/router/frontend (le endpoint GET /promotion/
    mecanismes expose automatiquement les clés disponibles).

    `Promotion.valeur` (float) et `Promotion.parametres` (JSON libre) sont mis à
    disposition de chaque mécanisme pour ses propres besoins de configuration.
    """

    @abstractmethod
    def est_applicable(self, promo, contexte: PromotionContext) -> tuple[bool, str]:
        """Vérifie une condition métier propre au mécanisme (ex: plage horaire,
        montant minimum...). Les vérifications génériques (actif, dates,
        usage_max) sont déjà faites en amont par is_valide_promotion et n'ont pas
        besoin d'être répétées ici. Retourne (applicable, raison_si_non_applicable)."""
        ...

    @abstractmethod
    def calculer_reduction(self, promo, contexte: PromotionContext) -> float:
        """Retourne le MONTANT de la réduction à soustraire (pas le prix final)."""
        ...
