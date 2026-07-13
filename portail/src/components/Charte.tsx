import { useState } from "react";
import { ScrollText } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";
import { Brand, useConfigPublique } from "./Brand";

/** Lien + modale de lecture de la charte d'utilisation. */
export function CharteLien({ label = "charte d'utilisation" }: { label?: string }) {
  const config = useConfigPublique();
  const [ouverte, setOuverte] = useState(false);
  if (!config?.charte?.trim()) return <span>{label}</span>;
  return (
    <>
      <button
        type="button"
        onClick={() => setOuverte(true)}
        style={{ background: "none", border: "none", color: "var(--accent)", textDecoration: "underline", cursor: "pointer", padding: 0, font: "inherit" }}
      >
        {label}
      </button>
      {ouverte && (
        <div
          onClick={() => setOuverte(false)}
          style={{
            position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.55)",
            display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
          }}
        >
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 560, maxHeight: "80vh", overflowY: "auto", width: "100%" }}>
            <h2 style={{ fontSize: 17, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <ScrollText size={18} /> Charte d'utilisation
            </h2>
            <p style={{ whiteSpace: "pre-line", fontSize: 14, lineHeight: 1.6 }}>{config.charte}</p>
            <button className="btn btn-primary btn-block" style={{ marginTop: 16 }} onClick={() => setOuverte(false)}>
              Fermer
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/** Écran bloquant d'acceptation de la charte pour un compte connecté qui ne l'a
 * pas encore acceptée (le serveur mémorise la date d'acceptation). */
export function CharteGate() {
  const config = useConfigPublique();
  const { rechargerProfil, logout } = usePortalAuth();
  const [coche, setCoche] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function accepter() {
    setSaving(true);
    setError(null);
    try {
      await api.post("/portail/moi/accepter-charte");
      await rechargerProfil();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="public-shell">
      <div className="public-card">
        <Brand sousTitre="Avant de continuer" />
        <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <h2 style={{ fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <ScrollText size={17} /> Charte d'utilisation
          </h2>
          <div style={{ maxHeight: 300, overflowY: "auto", background: "var(--surface-2)", borderRadius: 12, padding: 14 }}>
            <p style={{ whiteSpace: "pre-line", fontSize: 13.5, lineHeight: 1.6 }}>{config?.charte}</p>
          </div>
          {error && <p className="error">{error}</p>}
          <label style={{ flexDirection: "row", alignItems: "center", gap: 10, fontWeight: 500, color: "var(--text)" }}>
            <input type="checkbox" checked={coche} onChange={(e) => setCoche(e.target.checked)} style={{ width: "auto" }} />
            J'ai lu et j'accepte la charte d'utilisation
          </label>
          <button className="btn btn-primary btn-lg btn-block" onClick={accepter} disabled={!coche || saving}>
            {saving ? "Validation..." : "Continuer"}
          </button>
          <button className="btn btn-ghost" onClick={logout}>
            Refuser et se déconnecter
          </button>
        </div>
      </div>
    </div>
  );
}
