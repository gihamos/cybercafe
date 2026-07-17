import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { KeyRound, Ticket, UserRound, Wallet } from "lucide-react";
import { ApiError } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";
import { AnnonceBanner } from "../components/AnnonceBanner";
import { Brand, useConfigPublique } from "../components/Brand";
import { CharteLien } from "../components/Charte";
import { LimiteSessionsModal } from "../components/LimiteSessionsModal";
import type { LimiteSessionsDetail } from "../api/types";

export default function ConnexionPage() {
  const { loginCompte, loginTicket } = usePortalAuth();
  const config = useConfigPublique();
  const charteRequise = Boolean(config?.charte?.trim());
  const [charteAcceptee, setCharteAcceptee] = useState(false);
  const navigate = useNavigate();
  const [onglet, setOnglet] = useState<"compte" | "ticket">("compte");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [limiteDetail, setLimiteDetail] = useState<LimiteSessionsDetail | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (onglet === "compte") {
        await loginCompte(username, password);
        navigate("/", { replace: true });
      } else {
        if (charteRequise && !charteAcceptee) {
          throw new ApiError("Vous devez accepter la charte d'utilisation", 400);
        }
        await loginTicket(code);
        navigate("/wifi", { replace: true });
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && (err.detail as LimiteSessionsDetail)?.code === "limite_sessions_atteinte") {
        setLimiteDetail(err.detail as LimiteSessionsDetail);
      } else {
        setError(err instanceof ApiError ? err.message : "Connexion impossible");
      }
    } finally {
      setLoading(false);
    }
  }

  async function confirmerDeconnexion() {
    if (!limiteDetail) return;
    setLoading(true);
    try {
      await loginTicket(code, limiteDetail.session_a_deconnecter.id);
      setLimiteDetail(null);
      navigate("/wifi", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connexion impossible");
      setLimiteDetail(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="public-shell">
      <div className="public-card">
        <Brand sousTitre="Connectez-vous pour accéder au WiFi et à votre espace" accueil />

        <AnnonceBanner />

        {config?.message_connexion?.trim() && (
          <p className="muted" style={{ fontSize: 13, textAlign: "center", whiteSpace: "pre-line" }}>
            {config.message_connexion}
          </p>
        )}

        <div className="tabs">
          <button className={onglet === "compte" ? "active" : ""} onClick={() => setOnglet("compte")}>
            <UserRound size={14} style={{ verticalAlign: "-2px" }} /> Mon compte
          </button>
          <button className={onglet === "ticket" ? "active" : ""} onClick={() => setOnglet("ticket")}>
            <Ticket size={14} style={{ verticalAlign: "-2px" }} /> Code ticket
          </button>
        </div>

        <form className="card fade-in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <p className="error">{error}</p>}

          {onglet === "compte" ? (
            <>
              <label>
                Nom d'utilisateur
                <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus autoComplete="username" />
              </label>
              <label>
                Mot de passe
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
              </label>
            </>
          ) : (
            <label>
              Code du ticket
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                required
                autoFocus
                placeholder="ex : A1B2C3D4E5"
                style={{ textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, textAlign: "center" }}
              />
            </label>
          )}

          {onglet === "ticket" && charteRequise && (
            <label style={{ flexDirection: "row", alignItems: "center", gap: 10, fontWeight: 500, color: "var(--text)", fontSize: 13.5 }}>
              <input type="checkbox" checked={charteAcceptee} onChange={(e) => setCharteAcceptee(e.target.checked)} style={{ width: "auto" }} />
              <span>
                J'accepte la <CharteLien />
              </span>
            </label>
          )}

          <button className="btn btn-primary btn-lg btn-block" type="submit" disabled={loading}>
            <KeyRound size={17} /> {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span className="muted" style={{ fontSize: 13, textAlign: "center" }}>Pas encore de ticket ou de crédit ?</span>
          <div style={{ display: "flex", gap: 10 }}>
            <Link className="btn btn-block" to="/acheter-ticket">
              <Ticket size={15} /> Acheter un ticket
            </Link>
            <Link className="btn btn-block" to="/recharger">
              <Wallet size={15} /> Recharger un compte
            </Link>
          </div>
        </div>
      </div>

      {limiteDetail && (
        <LimiteSessionsModal
          detail={limiteDetail}
          busy={loading}
          onConfirm={confirmerDeconnexion}
          onCancel={() => setLimiteDetail(null)}
        />
      )}
    </div>
  );
}
