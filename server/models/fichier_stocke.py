from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base


class FichierStocke(Base):
    """Fichier dans l'espace de stockage réseau. Deux propriétaires possibles,
    mutuellement exclusifs :
    - user_id : stockage persistant d'un compte (client/opérateur/admin), soumis à quota,
      accessible depuis n'importe quel poste après connexion.
    - ticket_id : stockage temporaire d'une session par code/ticket (anonyme), purgé
      automatiquement à la fermeture de la session (voir SessionService.fermer_session)."""

    __tablename__ = "fichiers_stockes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)

    user = relationship("User", backref="fichiers_stockes")
    ticket = relationship("Ticket", backref="fichiers_stockes")

    nom_original = Column(String, nullable=False)
    # Fournisseur de stockage ayant reçu le fichier (voir services/storage_provider/)
    provider = Column(String, nullable=False, default="local")
    # Clé/chemin interne au provider, opaque pour l'appelant
    cle_stockage = Column(String, nullable=False)
    taille_octets = Column(Integer, nullable=False)
    content_type = Column(String, nullable=True)

    date_upload = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL) OR (ticket_id IS NOT NULL)",
            name="check_fichier_proprietaire"
        ),
    )
