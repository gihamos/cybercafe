import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { useAuth } from "./AuthContext";

export default function LoginPage() {
  const { login, loading, user } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    }
  }

  if (user && user.role === "client") {
    return (
      <div className="login-page">
        <div className="login-form">
          <p className="error">Ce panneau est réservé aux administrateurs et opérateurs.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit} className="login-form">
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>
          <div className="sidebar-brand-mark" style={{ width: 40, height: 40, borderRadius: 12 }}>
            <Zap size={20} />
          </div>
        </div>
        <h1>Cybercafé — Administration</h1>
        {error && <p className="error">{error}</p>}
        <label>
          Nom d'utilisateur
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Mot de passe
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Connexion..." : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
