import { AlertTriangle, X } from "lucide-react";
import type { LimiteSessionsDetail } from "../api/types";

const PORTEE_LABEL: Record<LimiteSessionsDetail["portee"], string> = {
  ticket: "ce ticket",
  forfait: "ce forfait",
  compte: "votre compte",
};

/** Proposition de déconnexion quand le plafond de connexions simultanées (ticket,
 * forfait ou compte — voir server/services/portail_service.py::verifier_limite_sessions)
 * est atteint : le client choisit de déconnecter la session la plus ancienne pour
 * continuer, ou annule. */
export function LimiteSessionsModal({
  detail,
  busy,
  onConfirm,
  onCancel,
}: {
  detail: LimiteSessionsDetail;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const s = detail.session_a_deconnecter;
  return (
    <div
      onClick={onCancel}
      style={{
        position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.55)",
        display: "flex", alignItems: "flex-end", justifyContent: "center", padding: 16,
      }}
    >
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={17} style={{ color: "var(--warning, #d97706)" }} /> Limite de connexions atteinte
          </h2>
          <button className="icon-btn" onClick={onCancel}>
            <X size={18} />
          </button>
        </div>
        <p className="muted" style={{ fontSize: 13.5 }}>
          {PORTEE_LABEL[detail.portee]} autorise au maximum {detail.limite} connexion{detail.limite > 1 ? "s" : ""} simultanée{detail.limite > 1 ? "s" : ""}.
          Pour continuer, déconnectez la session la plus ancienne :
        </p>
        <div className="liste-item" style={{ padding: "10px 0" }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>{s.poste_nom || "WiFi"}</div>
            <span className="muted" style={{ fontSize: 12.5 }}>Connectée depuis le {new Date(s.date_debut).toLocaleString()}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-block" onClick={onCancel} disabled={busy}>
            Annuler
          </button>
          <button className="btn btn-primary btn-block" onClick={onConfirm} disabled={busy}>
            {busy ? "..." : "Déconnecter et continuer"}
          </button>
        </div>
      </div>
    </div>
  );
}
