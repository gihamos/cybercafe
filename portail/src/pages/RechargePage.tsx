import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Ticket, Wallet } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";
import { PaiementEnLigne } from "../components/PaiementEnLigne";
import type { CommandeEnLigne } from "../api/types";

const MONTANTS = [5, 10, 20, 30, 50];

export default function RechargePage() {
  const { profil, rechargerProfil } = usePortalAuth();
  const navigate = useNavigate();
  const [codeBon, setCodeBon] = useState("");
  const [bonMessage, setBonMessage] = useState<string | null>(null);
  const [bonError, setBonError] = useState<string | null>(null);
  const [bonSaving, setBonSaving] = useState(false);
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
      const cmd = await api.post<CommandeEnLigne>("/portail/recharge/commande", {
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

  async function onSucces() {
    setSucces(true);
    await rechargerProfil();
  }

  async function utiliserBon(e: FormEvent) {
    e.preventDefault();
    setBonError(null);
    setBonMessage(null);
    setBonSaving(true);
    try {
      const result = await api.post<{ credit_euros: number; nouveau_solde: number }>("/portail/recharge/code", {
        code: codeBon.trim().toUpperCase(),
      });
      setBonMessage(`+${result.credit_euros.toFixed(2)}€ crédités — nouveau solde : ${result.nouveau_solde.toFixed(2)}€`);
      setCodeBon("");
      await rechargerProfil();
    } catch (err) {
      setBonError(err instanceof ApiError ? err.message : "Code invalide");
    } finally {
      setBonSaving(false);
    }
  }

  return (
    <>
      <div className="section-titre">
        <Wallet size={17} /> Recharger mon compte
      </div>

      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="muted">Solde actuel</span>
        <strong style={{ fontSize: 22 }}>{profil?.solde_euros.toFixed(2)}€</strong>
      </div>

      {succes ? (
        <div className="card fade-in" style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12 }}>
          <span className="badge badge-success" style={{ alignSelf: "center" }}>Recharge confirmée</span>
          <p>
            Votre compte a été crédité de <strong>{parseFloat(montant).toFixed(2)}€</strong>.
          </p>
          <button className="btn btn-primary" onClick={() => navigate("/")}>Retour à l'accueil</button>
        </div>
      ) : commande ? (
        <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="liste-item" style={{ borderBottom: "none", padding: 0 }}>
            <span>Recharge de solde</span>
            <strong>{parseFloat(montant).toFixed(2)}€</strong>
          </div>
          <PaiementEnLigne commande={commande} onSucces={onSucces} />
        </div>
      ) : (
        <form className="card fade-in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <p className="error">{error}</p>}
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
              <option value="paypal">PayPal</option>
              <option value="carte">Carte bancaire</option>
              <option value="mobile_money">Mobile money</option>
              <option value="demo">Passerelle démo (test)</option>
            </select>
          </label>
          <button className="btn btn-primary btn-lg btn-block" type="submit" disabled={loading}>
            <Wallet size={17} /> {loading ? "Création..." : "Recharger"}
          </button>
        </form>
      )}

      <form className="card fade-in" onSubmit={utiliserBon} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="section-titre">
          <Ticket size={15} /> J'ai un bon de recharge
        </div>
        <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>
          Saisissez le code du bon acheté au comptoir : son montant est crédité immédiatement sur votre solde.
        </p>
        {bonError && <p className="error">{bonError}</p>}
        {bonMessage && <p className="success-box">{bonMessage}</p>}
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={codeBon}
            onChange={(e) => setCodeBon(e.target.value.toUpperCase())}
            placeholder="ex : A1B2C3D4E5"
            style={{ textTransform: "uppercase", letterSpacing: "0.12em", fontWeight: 700 }}
            required
          />
          <button className="btn btn-primary" type="submit" disabled={bonSaving} style={{ flexShrink: 0 }}>
            {bonSaving ? "..." : "Utiliser"}
          </button>
        </div>
      </form>
    </>
  );
}
