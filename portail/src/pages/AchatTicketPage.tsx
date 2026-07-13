import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Clock, Copy, Database, Infinity as InfinityIcon, Ticket } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { CommandeEnLigne, OffrePublique, StatutCommande } from "../api/types";
import { Brand } from "../components/Brand";
import { PaiementEnLigne } from "../components/PaiementEnLigne";

const TYPE_ICON = { temps: Clock, data: Database, illimite: InfinityIcon };

function detailOffre(o: OffrePublique): string {
  if (o.type_offre === "temps" && o.duree_minutes != null) {
    return o.duree_minutes >= 60 ? `${Math.round(o.duree_minutes / 60)}h de connexion` : `${o.duree_minutes} min de connexion`;
  }
  if (o.type_offre === "data" && o.quota_mo != null) {
    return o.quota_mo >= 1024 ? `${(o.quota_mo / 1024).toFixed(1)} Go de données` : `${o.quota_mo} Mo de données`;
  }
  return "Accès illimité";
}

export default function AchatTicketPage() {
  const [offres, setOffres] = useState<OffrePublique[]>([]);
  const [selection, setSelection] = useState<OffrePublique | null>(null);
  const [gateway, setGateway] = useState("demo");
  const [commande, setCommande] = useState<CommandeEnLigne | null>(null);
  const [codeTicket, setCodeTicket] = useState<string | null>(null);
  const [copie, setCopie] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<OffrePublique[]>("/portail/public/offres").then(setOffres).catch(() => {});
  }, []);

  async function commander() {
    if (!selection) return;
    setError(null);
    setLoading(true);
    try {
      const cmd = await api.post<CommandeEnLigne>("/portail/public/ticket/commande", {
        offre_id: selection.id,
        gateway,
      });
      setCommande(cmd);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la commande");
    } finally {
      setLoading(false);
    }
  }

  function onSucces(statut: StatutCommande) {
    if (statut.ticket_code) setCodeTicket(statut.ticket_code);
  }

  return (
    <div className="public-shell">
      <div className="public-card">
        <Link to="/connexion" className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }}>
          <ArrowLeft size={15} /> Retour
        </Link>
        <Brand sousTitre="Achetez un ticket de connexion en ligne" />

        {codeTicket ? (
          <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 14, textAlign: "center" }}>
            <span className="badge badge-success" style={{ alignSelf: "center" }}>Paiement confirmé</span>
            <h2 style={{ fontSize: 17 }}>Votre code de connexion</h2>
            <div
              style={{
                fontSize: 26, fontWeight: 800, letterSpacing: "0.2em",
                padding: "16px 8px", borderRadius: 14, background: "var(--surface-2)",
              }}
            >
              {codeTicket}
            </div>
            <button
              className="btn"
              onClick={() => {
                navigator.clipboard?.writeText(codeTicket);
                setCopie(true);
                setTimeout(() => setCopie(false), 2000);
              }}
            >
              <Copy size={15} /> {copie ? "Copié !" : "Copier le code"}
            </button>
            <p className="muted" style={{ fontSize: 13 }}>
              Conservez ce code précieusement : il vous servira à vous connecter au WiFi.
            </p>
            <Link className="btn btn-primary btn-block" to="/connexion">
              Se connecter avec ce code
            </Link>
          </div>
        ) : commande ? (
          <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="liste-item" style={{ borderBottom: "none", padding: 0 }}>
              <strong>{selection?.nom}</strong>
              <strong>{commande.montant?.toFixed(2)}€</strong>
            </div>
            <PaiementEnLigne commande={commande} onSucces={onSucces} />
          </div>
        ) : (
          <>
            {error && <p className="error">{error}</p>}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {offres.length === 0 && <div className="card empty-state">Aucun forfait disponible</div>}
              {offres.map((o) => {
                const Icone = TYPE_ICON[o.type_offre] || Ticket;
                const actif = selection?.id === o.id;
                return (
                  <button
                    key={o.id}
                    className="card fade-in"
                    onClick={() => setSelection(o)}
                    style={{
                      display: "flex", alignItems: "center", gap: 14, textAlign: "left",
                      borderColor: actif ? "var(--accent)" : "var(--border)",
                      borderWidth: 1.5,
                      background: actif ? "color-mix(in srgb, var(--accent) 7%, var(--surface))" : "var(--surface)",
                    }}
                  >
                    <div
                      style={{
                        width: 44, height: 44, borderRadius: 13, flexShrink: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: "color-mix(in srgb, var(--accent) 13%, transparent)", color: "var(--accent)",
                      }}
                    >
                      <Icone size={20} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 800 }}>{o.nom}</div>
                      <div className="muted" style={{ fontSize: 13 }}>{detailOffre(o)}</div>
                    </div>
                    <div style={{ fontWeight: 800, fontSize: 17 }}>{o.prix.toFixed(2)}€</div>
                  </button>
                );
              })}
            </div>

            {selection && (
              <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <label>
                  Moyen de paiement
                  <select value={gateway} onChange={(e) => setGateway(e.target.value)}>
                    <option value="paypal">PayPal</option>
                    <option value="carte">Carte bancaire</option>
                    <option value="mobile_money">Mobile money</option>
                    <option value="demo">Passerelle démo (test)</option>
                  </select>
                </label>
                <button className="btn btn-primary btn-lg btn-block" onClick={commander} disabled={loading}>
                  <Ticket size={17} /> {loading ? "Création..." : `Payer ${selection.prix.toFixed(2)}€`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
