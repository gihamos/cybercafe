import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Wallet } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { CommandeEnLigne } from "../api/types";
import { Brand } from "../components/Brand";
import { PaiementEnLigne } from "../components/PaiementEnLigne";

const MONTANTS = [5, 10, 20, 30, 50];

export default function RechargePubliquePage() {
  const [username, setUsername] = useState("");
  const [montant, setMontant] = useState("10");
  const [gateway, setGateway] = useState("demo");
  const [commande, setCommande] = useState<CommandeEnLigne | null>(null);
  const [succes, setSucces] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const cmd = await api.post<CommandeEnLigne>("/portail/public/recharge/commande", {
        username: username.trim(),
        montant: parseFloat(montant),
        gateway,
      });
      setCommande(cmd);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la commande");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="public-shell">
      <div className="public-card">
        <Link to="/connexion" className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }}>
          <ArrowLeft size={15} /> Retour
        </Link>
        <Brand sousTitre="Rechargez le solde d'un compte client" />

        {succes ? (
          <div className="card fade-in" style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12 }}>
            <span className="badge badge-success" style={{ alignSelf: "center" }}>Recharge confirmée</span>
            <p>
              Le compte <strong>{username}</strong> a été crédité de <strong>{parseFloat(montant).toFixed(2)}€</strong>.
            </p>
            <Link className="btn btn-primary btn-block" to="/connexion">Se connecter</Link>
          </div>
        ) : commande ? (
          <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="liste-item" style={{ borderBottom: "none", padding: 0 }}>
              <span>
                Recharge du compte <strong>{username}</strong>
              </span>
              <strong>{parseFloat(montant).toFixed(2)}€</strong>
            </div>
            <PaiementEnLigne commande={commande} onSucces={() => setSucces(true)} />
          </div>
        ) : (
          <form className="card fade-in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {error && <p className="error">{error}</p>}
            <label>
              Nom d'utilisateur du compte
              <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
            </label>
            <label>
              Montant (€)
              <input type="number" min="1" step="0.5" value={montant} onChange={(e) => setMontant(e.target.value)} required />
            </label>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {MONTANTS.map((m) => (
                <button
                  type="button"
                  key={m}
                  className="btn btn-sm"
                  style={montant === String(m) ? { borderColor: "var(--accent)", color: "var(--accent)" } : undefined}
                  onClick={() => setMontant(String(m))}
                >
                  {m}€
                </button>
              ))}
            </div>
            <label>
              Moyen de paiement
              <select value={gateway} onChange={(e) => setGateway(e.target.value)}>
                <option value="paypal">PayPal / Carte bancaire</option>
                <option value="demo">Passerelle démo (test)</option>
              </select>
            </label>
            <button className="btn btn-primary btn-lg btn-block" type="submit" disabled={loading}>
              <Wallet size={17} /> {loading ? "Création..." : "Recharger"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
