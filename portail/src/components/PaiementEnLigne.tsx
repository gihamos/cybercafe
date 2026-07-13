import { useEffect, useRef, useState } from "react";
import { CheckCircle2, ExternalLink, Loader2 } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { CommandeEnLigne, StatutCommande } from "../api/types";

/** Suivi d'une commande en ligne : pour une vraie passerelle (PayPal...), ouvre
 * l'approval_url et sonde le statut jusqu'à confirmation par le webhook ; pour la
 * passerelle démo (approval_url en demo://), affiche un bouton de confirmation qui
 * simule le retour de paiement. */
export function PaiementEnLigne({
  commande,
  onSucces,
}: {
  commande: CommandeEnLigne;
  onSucces: (statut: StatutCommande) => void;
}) {
  const [statut, setStatut] = useState<StatutCommande | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const onSuccesRef = useRef(onSucces);
  onSuccesRef.current = onSucces;

  const estDemo = commande.approval_url.startsWith("demo://");

  useEffect(() => {
    let arret = false;
    const interval = setInterval(async () => {
      try {
        const s = await api.get<StatutCommande>(
          `/portail/public/commande/${commande.paiement_id}/statut?secret=${commande.secret}`
        );
        if (arret) return;
        setStatut(s);
        if (s.statut === "succes") {
          clearInterval(interval);
          onSuccesRef.current(s);
        }
      } catch {
        /* réseau : on réessaie au tick suivant */
      }
    }, 2500);
    return () => {
      arret = true;
      clearInterval(interval);
    };
  }, [commande.paiement_id, commande.secret]);

  async function confirmerDemo() {
    setConfirming(true);
    setError(null);
    try {
      await api.post(`/portail/public/commande/${commande.paiement_id}/confirmer-demo`, {
        secret: commande.secret,
      });
      const s = await api.get<StatutCommande>(
        `/portail/public/commande/${commande.paiement_id}/statut?secret=${commande.secret}`
      );
      setStatut(s);
      if (s.statut === "succes") onSuccesRef.current(s);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la confirmation");
    } finally {
      setConfirming(false);
    }
  }

  if (statut?.statut === "succes") {
    return (
      <div className="success-box" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <CheckCircle2 size={18} /> Paiement confirmé !
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {error && <p className="error">{error}</p>}
      {estDemo ? (
        <button className="btn btn-primary btn-block" onClick={confirmerDemo} disabled={confirming}>
          {confirming ? <Loader2 size={16} className="spin" /> : null}
          {confirming ? "Confirmation..." : "Payer maintenant (démo)"}
        </button>
      ) : (
        <>
          <a className="btn btn-primary btn-block" href={commande.approval_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} /> Payer sur la plateforme sécurisée
          </a>
          <p className="muted" style={{ fontSize: 13, textAlign: "center" }}>
            <Loader2 size={13} style={{ verticalAlign: "-2px" }} /> En attente de la confirmation du paiement...
          </p>
        </>
      )}
    </div>
  );
}
