import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Package, Play, Repeat, Square, Ticket as TicketIcon, Wallet, Wifi } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";
import { TicketPickerModal } from "../components/TicketPickerModal";
import type { SessionWifi, TicketChoix } from "../api/types";

function formatMinutes(min: number | null): string {
  if (min == null) return "Illimité";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}` : `${m} min`;
}

export default function TableauBordPage() {
  const { profil, rechargerProfil } = usePortalAuth();
  const [session, setSession] = useState<SessionWifi | null>(null);
  const [tickets, setTickets] = useState<TicketChoix[]>([]);
  const [showPicker, setShowPicker] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const rafraichir = useCallback(async () => {
    try {
      const s = await api.get<SessionWifi | null>("/portail/session");
      setSession(s);
    } catch {
      /* silencieux */
    }
  }, []);

  const rafraichirTickets = useCallback(async () => {
    try {
      const t = await api.get<TicketChoix[]>("/portail/mes-tickets");
      setTickets(t);
    } catch {
      /* silencieux */
    }
  }, []);

  useEffect(() => {
    rafraichir();
    rafraichirTickets();
    const interval = setInterval(rafraichir, 30000);
    return () => clearInterval(interval);
  }, [rafraichir, rafraichirTickets]);

  const abo = profil?.abonnement_courant;
  const totalOptions = tickets.length + (abo ? 1 : 0);

  async function demarrer() {
    setError(null);
    setBusy(true);
    try {
      const s = await api.post<SessionWifi>("/portail/session/demarrer");
      setSession(s);
    } catch (err) {
      // le serveur répond ainsi quand plusieurs forfaits (abonnement et/ou
      // tickets) sont utilisables et qu'aucun ne peut être choisi automatiquement
      if (err instanceof ApiError && totalOptions > 1) {
        setShowPicker(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Impossible de démarrer la session");
      }
    } finally {
      setBusy(false);
    }
  }

  async function terminer() {
    setBusy(true);
    try {
      const s = await api.post<SessionWifi>("/portail/session/terminer");
      setSession(s);
      await rechargerProfil();
      await rafraichirTickets();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  function onTicketChoisi(s: SessionWifi) {
    setSession(s);
    setShowPicker(false);
    rechargerProfil();
    rafraichirTickets();
  }

  const active = session?.est_active;
  const pct =
    session && session.limite_minutes
      ? Math.min(100, Math.round(((session.consommation_minutes || 0) / session.limite_minutes) * 100))
      : 0;

  return (
    <>
      <div className="card session-hero fade-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800, fontSize: 16 }}>
            <Wifi size={19} /> {active ? "Connecté au WiFi" : "WiFi non connecté"}
          </span>
          {active && <span className="badge" style={{ background: "rgba(255,255,255,0.22)", color: "#fff" }}>En cours</span>}
        </div>

        {active && session ? (
          <>
            <div>
              <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: "-0.02em" }}>
                {formatMinutes(session.restant_minutes)}
              </div>
              <span className="muted">
                {session.ticket_code ? `Ticket ${session.ticket_code}` : "temps restant aujourd'hui"}
              </span>
            </div>
            {session.limite_minutes != null && (
              <div className="progress">
                <div style={{ width: `${100 - pct}%` }} />
              </div>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              {totalOptions > 1 && (
                <button
                  className="btn"
                  style={{ background: "rgba(255,255,255,0.92)", border: "none" }}
                  onClick={() => setShowPicker(true)}
                >
                  <Repeat size={15} /> Changer de forfait
                </button>
              )}
              <button className="btn btn-block" style={{ background: "rgba(255,255,255,0.92)", border: "none" }} onClick={terminer} disabled={busy}>
                <Square size={15} /> Terminer la session
              </button>
            </div>
          </>
        ) : (
          <>
            <span className="muted">
              {totalOptions === 0
                ? "Aucun forfait actif : achetez un forfait ou un ticket pour vous connecter."
                : abo && tickets.length === 0
                  ? `Forfait « ${abo.offre_nom} » — ${abo.illimite ? "illimité" : formatMinutes(abo.minutes_restantes_aujourdhui) + " disponibles aujourd'hui"}`
                  : totalOptions === 1
                    ? "1 ticket disponible"
                    : `${totalOptions} forfaits disponibles`}
            </span>
            {abo && tickets.length === 0 && (
              <button className="btn btn-lg btn-block" style={{ background: "rgba(255,255,255,0.92)", border: "none" }} onClick={demarrer} disabled={busy}>
                <Play size={17} /> {busy ? "Connexion..." : "Se connecter au WiFi"}
              </button>
            )}
            {!abo && tickets.length === 1 && (
              <button
                className="btn btn-lg btn-block"
                style={{ background: "rgba(255,255,255,0.92)", border: "none" }}
                onClick={() => setShowPicker(true)}
              >
                <TicketIcon size={17} /> Se connecter avec mon ticket
              </button>
            )}
            {totalOptions > 1 && (
              <button
                className="btn btn-lg btn-block"
                style={{ background: "rgba(255,255,255,0.92)", border: "none" }}
                onClick={() => setShowPicker(true)}
              >
                <TicketIcon size={17} /> Choisir un forfait ({totalOptions})
              </button>
            )}
            {totalOptions === 0 && (
              <Link className="btn btn-lg btn-block" style={{ background: "rgba(255,255,255,0.92)", border: "none", color: "var(--accent)" }} to="/boutique">
                <Package size={17} /> Voir les forfaits
              </Link>
            )}
          </>
        )}
      </div>

      {error && <p className="error fade-in">{error}</p>}

      <div className="stat-grid">
        <div className="card stat-tile">
          <span className="label">Mon solde</span>
          <span className="valeur">{profil?.solde_euros.toFixed(2)}€</span>
          <Link to="/recharge" className="btn btn-sm" style={{ alignSelf: "flex-start", marginTop: 4 }}>
            <Wallet size={13} /> Recharger
          </Link>
        </div>
        <div className="card stat-tile">
          <span className="label">Forfait</span>
          <span className="valeur" style={{ fontSize: 17 }}>{abo?.offre_nom || "Aucun"}</span>
          {abo && (
            <span className="muted" style={{ fontSize: 12.5 }}>
              {abo.illimite
                ? "Accès illimité"
                : abo.minutes_restantes_aujourdhui != null
                  ? `${formatMinutes(abo.minutes_restantes_aujourdhui)} restants aujourd'hui`
                  : abo.data_restante_mo != null
                    ? `${abo.data_restante_mo.toFixed(0)} Mo restants`
                    : "Actif"}
            </span>
          )}
        </div>
        <div className="card stat-tile">
          <span className="label">Espace fichiers</span>
          <span className="valeur" style={{ fontSize: 17 }}>
            {profil ? `${(profil.stockage.usage_octets / (1024 * 1024)).toFixed(1)} Mo` : "—"}
          </span>
          <span className="muted" style={{ fontSize: 12.5 }}>sur {profil?.stockage.quota_mo.toFixed(0)} Mo</span>
        </div>
      </div>

      {showPicker && (
        <TicketPickerModal
          tickets={tickets}
          abonnement={abo}
          sessionActive={Boolean(active)}
          onClose={() => setShowPicker(false)}
          onChoisi={onTicketChoisi}
        />
      )}
    </>
  );
}
