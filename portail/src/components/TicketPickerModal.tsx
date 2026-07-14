import { useState } from "react";
import { Package, Ticket, X } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { AbonnementCourant, SessionWifi, TicketChoix } from "../api/types";

const CLE_ABO = -1;

function formatRestant(t: TicketChoix): string {
  const parts: string[] = [];
  if (t.restant_minutes != null) parts.push(`${t.restant_minutes} min`);
  if (t.restant_data_mo != null) parts.push(`${t.restant_data_mo.toFixed(0)} Mo`);
  return parts.length > 0 ? parts.join(" · ") : "—";
}

function formatRestantAbo(a: AbonnementCourant): string {
  if (a.illimite) return "Illimité";
  const parts: string[] = [];
  if (a.minutes_restantes_aujourdhui != null) parts.push(`${a.minutes_restantes_aujourdhui} min`);
  if (a.data_restante_mo != null) parts.push(`${a.data_restante_mo.toFixed(0)} Mo`);
  return parts.length > 0 ? parts.join(" · ") : "—";
}

/** Choix du forfait à utiliser pour se connecter — un client peut posséder
 * plusieurs forfaits actifs à la fois (un abonnement et/ou plusieurs tickets,
 * achetés en caisse ou en ligne) et changer à tout moment, y compris pendant
 * qu'une session est déjà en cours. */
export function TicketPickerModal({
  tickets,
  abonnement,
  sessionActive,
  onClose,
  onChoisi,
}: {
  tickets: TicketChoix[];
  abonnement?: AbonnementCourant | null;
  sessionActive: boolean;
  onClose: () => void;
  onChoisi: (session: SessionWifi) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function choisir(ticketId: number | null) {
    setError(null);
    setBusyId(ticketId ?? CLE_ABO);
    try {
      const chemin = sessionActive ? "/portail/session/changer-ticket" : "/portail/session/demarrer";
      const session = await api.post<SessionWifi>(
        chemin,
        ticketId != null ? { ticket_id: ticketId } : { utiliser_abonnement: true }
      );
      onChoisi(session);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.55)",
        display: "flex", alignItems: "flex-end", justifyContent: "center", padding: 16,
      }}
    >
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Ticket size={17} /> Choisissez un forfait
          </h2>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>
          Vous avez plusieurs forfaits actifs — {sessionActive ? "changez de forfait à tout moment." : "choisissez celui à utiliser pour vous connecter."}
        </p>
        {error && <p className="error">{error}</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {abonnement && (
            <button
              className="btn"
              style={{ justifyContent: "space-between", padding: "12px 14px" }}
              onClick={() => choisir(null)}
              disabled={busyId !== null}
            >
              <span style={{ textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}>
                <Package size={15} />
                <strong>{abonnement.offre_nom || "Forfait"}</strong>
              </span>
              <span style={{ fontWeight: 700 }}>
                {busyId === CLE_ABO ? "..." : formatRestantAbo(abonnement)}
              </span>
            </button>
          )}
          {tickets.map((t) => (
            <button
              key={t.id}
              className="btn"
              style={{ justifyContent: "space-between", padding: "12px 14px" }}
              onClick={() => choisir(t.id)}
              disabled={busyId !== null}
            >
              <span style={{ textAlign: "left" }}>
                <strong>{t.offre_nom || "Ticket"}</strong>
                <div className="muted" style={{ fontSize: 12 }}>
                  <code>{t.code}</code>
                </div>
              </span>
              <span style={{ fontWeight: 700 }}>
                {busyId === t.id ? "..." : formatRestant(t)}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
