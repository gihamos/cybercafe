import { useState } from "react";
import { Ticket, X } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { SessionWifi, TicketChoix } from "../api/types";

function formatRestant(t: TicketChoix): string {
  const parts: string[] = [];
  if (t.restant_minutes != null) parts.push(`${t.restant_minutes} min`);
  if (t.restant_data_mo != null) parts.push(`${t.restant_data_mo.toFixed(0)} Mo`);
  return parts.length > 0 ? parts.join(" · ") : "—";
}

/** Choix du ticket à utiliser pour se connecter — un client peut posséder
 * plusieurs tickets actifs (achetés en caisse ou en ligne) et changer à tout
 * moment, y compris pendant qu'une session est déjà en cours. */
export function TicketPickerModal({
  tickets,
  sessionActive,
  onClose,
  onChoisi,
}: {
  tickets: TicketChoix[];
  sessionActive: boolean;
  onClose: () => void;
  onChoisi: (session: SessionWifi) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function choisir(ticket: TicketChoix) {
    setError(null);
    setBusyId(ticket.id);
    try {
      const chemin = sessionActive ? "/portail/session/changer-ticket" : "/portail/session/demarrer";
      const session = await api.post<SessionWifi>(chemin, { ticket_id: ticket.id });
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
            <Ticket size={17} /> Choisissez un ticket
          </h2>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>
          Vous avez plusieurs tickets actifs — {sessionActive ? "changez de ticket à tout moment." : "choisissez celui à utiliser pour vous connecter."}
        </p>
        {error && <p className="error">{error}</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {tickets.map((t) => (
            <button
              key={t.id}
              className="btn"
              style={{ justifyContent: "space-between", padding: "12px 14px" }}
              onClick={() => choisir(t)}
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
