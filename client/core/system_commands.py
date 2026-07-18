"""Dispatch des commandes système à privilèges élevés reçues du serveur (voir
main.py::_on_message, message WS "commande", et
server/services/Poste_service.py::envoyer_commande). Ce module ne contient
aucune logique spécifique à un OS — seulement la validation des paramètres et
le routage vers platform_/ (même séparation que le durcissement kiosk :
platform_/ = primitives OS brutes, core/ = logique métier qui s'y branche).

Nécessite que le process client tourne avec des droits suffisants — voir
packaging/kiosk_deployment.md § Niveau de privilège requis. Aucune commande
shell=True ni concaténation de chaîne : tout passe par des listes d'arguments
explicites côté platform_/."""

import logging

import platform_

logger = logging.getLogger("cybercafe.client")

COMMANDE_REDEMARRER = "redemarrer"
COMMANDE_ETEINDRE = "eteindre"
COMMANDE_VERROUILLER_LECTEUR = "verrouiller_lecteur"
COMMANDE_DEVERROUILLER_LECTEUR = "deverrouiller_lecteur"


def executer_commande(commande: str, details: dict | None = None) -> bool:
    """Exécute une commande système. Retourne True si la commande a été reconnue
    et transmise à l'OS — pas de garantie sur son résultat effectif (ex: un
    redémarrage ne renvoie jamais de confirmation, le poste s'éteint)."""
    details = details or {}

    if commande == COMMANDE_REDEMARRER:
        platform_.redemarrer_poste()
        return True

    if commande == COMMANDE_ETEINDRE:
        platform_.eteindre_poste()
        return True

    if commande == COMMANDE_VERROUILLER_LECTEUR:
        identifiant = details.get("identifiant")
        if not identifiant:
            logger.warning("Commande verrouiller_lecteur reçue sans identifiant de lecteur")
            return False
        platform_.verrouiller_lecteur(identifiant)
        return True

    if commande == COMMANDE_DEVERROUILLER_LECTEUR:
        identifiant = details.get("identifiant")
        if not identifiant:
            logger.warning("Commande deverrouiller_lecteur reçue sans identifiant de lecteur")
            return False
        platform_.deverrouiller_lecteur(identifiant)
        return True

    logger.warning("Commande système inconnue reçue du serveur: %s", commande)
    return False
