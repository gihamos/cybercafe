import { useCallback, useEffect, useState } from "react";
import { LogOut, RefreshCw, Ticket, Wifi } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";
import { LimiteSessionsModal } from "../components/LimiteSessionsModal";
import type { LimiteSessionsDetail, SessionWifi } from "../api/types";
import { Brand } from "../components/Brand";

function formatMinutes(min: number | null): string {
  if (min == null) return "Illimité";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}min` : `${m} min`;
}

export default function TicketSessionPage() {
  const { ticketCode, loginTicket, logout } = usePortalAuth();
  const [session, setSession] = useState<SessionWifi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [terminee, setTerminee] = useState(false);
  const [limiteDetail, setLimiteDetail] = useState<LimiteSessionsDetail | null>(null);

  const rafraichir = useCallback(async () => {
    if (!ticketCode) return;
    try {
      const s = await api.get<SessionWifi | null>(`/portail/wifi/etat?code=${encodeURIComponent(ticketCode)}`);
      setSession(s);
      if (s && !s.est_active) setTerminee(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de connexion");
    }
  }, [ticketCode]);

  useEffect(() => {
    rafraichir();
    const interval = setInterval(rafraichir, 30000);
    return () => clearInterval(interval);
  }, [rafraichir]);

  async function reconnecter(deconnecterSessionId?: number) {
    if (!ticketCode) return;
    setError(null);
    try {
      const s = await loginTicket(ticketCode, deconnecterSessionId);
      setSession(s);
      setTerminee(false);
      setLimiteDetail(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && (err.detail as LimiteSessionsDetail)?.code === "limite_sessions_atteinte") {
        setLimiteDetail(err.detail as LimiteSessionsDetail);
      } else {
        setError(err instanceof ApiError ? err.message : "Reconnexion impossible");
      }
    }
  }

  async function deconnecter() {
    if (!ticketCode) return;
    try {
      await api.post("/portail/wifi/deconnexion", { code: ticketCode });
    } catch {
      /* la déconnexion locale reste valable */
    }
    logout();
  }

  const pct =
    session && session.limite_minutes
      ? Math.min(100, Math.round(((session.consommation_minutes || 0) / session.limite_minutes) * 100))
      : 0;

  return (
    <div className="public-shell">
      <div className="public-card">
        <Brand sousTitre="Accès WiFi par ticket" />

        {error && <p className="error">{error}</p>}

        <div className="card session-hero fade-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800 }}>
              <Wifi size={18} /> {terminee ? "Session terminée" : session ? "Connecté au WiFi" : "Session inactive"}
            </span>
            <span className="badge" style={{ background: "rgba(255,255,255,0.2)", color: "#fff" }}>
              <Ticket size={12} /> {ticketCode}
            </span>
          </div>

          {session && (
            <>
              <div>
                <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em" }}>
                  {formatMinutes(session.restant_minutes)}
                </div>
                <span className="muted">temps restant</span>
              </div>
              {session.limite_minutes != null && (
                <div className="progress">
                  <div style={{ width: `${100 - pct}%` }} />
                </div>
              )}
              <div className="muted" style={{ fontSize: 13 }}>
                Consommé : {session.consommation_minutes} min
                {session.limite_minutes != null && ` / ${session.limite_minutes} min`}
              </div>
            </>
          )}
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          {terminee || !session ? (
            <button className="btn btn-primary btn-block" onClick={() => reconnecter()}>
              <Wifi size={15} /> Se reconnecter
            </button>
          ) : (
            <button className="btn btn-block" onClick={rafraichir}>
              <RefreshCw size={15} /> Actualiser
            </button>
          )}
          <button className="btn btn-danger btn-block" onClick={deconnecter}>
            <LogOut size={15} /> Se déconnecter
          </button>
        </div>

        <p className="muted" style={{ fontSize: 12.5, textAlign: "center" }}>
          Le temps est décompté tant que la session est active. Pensez à vous déconnecter pour préserver votre ticket.
        </p>
      </div>

      {limiteDetail && (
        <LimiteSessionsModal
          detail={limiteDetail}
          onConfirm={() => reconnecter(limiteDetail.session_a_deconnecter.id)}
          onCancel={() => setLimiteDetail(null)}
        />
      )}
    </div>
  );
}
