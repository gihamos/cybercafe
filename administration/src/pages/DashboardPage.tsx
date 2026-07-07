import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ArticleVendu, RevenuJour, StatsResume } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<StatsResume | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<StatsResume>("/stats/resume")
      .then(setStats)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h1>Tableau de bord</h1>
      <p className="muted">
        Connecté en tant que <strong>{user?.username}</strong> ({user?.role}).
      </p>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Chargement...</p>}

      {stats && (
        <>
          <div className="stat-tiles">
            <StatTile label="Clients" value={stats.total_clients} />
            <StatTile label="Sessions actives" value={stats.sessions_actives} />
            <StatTile label="Sessions aujourd'hui" value={stats.sessions_aujourdhui} />
            <StatTile
              label="Postes occupés"
              value={`${stats.postes.occupes} / ${stats.postes.total}`}
              sub={`${stats.postes.taux_occupation}% d'occupation`}
            />
            <StatTile label="Revenu (30 jours)" value={`${stats.revenu_total_30j.toFixed(2)}€`} />
          </div>

          <div className="card">
            <h2>Revenus par jour (30 derniers jours)</h2>
            <RevenueBarChart data={stats.revenus_par_jour} />
          </div>

          <div className="card">
            <h2>Articles les plus vendus</h2>
            <TopArticlesChart data={stats.articles_plus_vendus} />
          </div>
        </>
      )}
    </div>
  );
}

function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="stat-tile">
      <span className="stat-tile-label">{label}</span>
      <span className="stat-tile-value">{value}</span>
      {sub && <span className="stat-tile-sub">{sub}</span>}
    </div>
  );
}

function RevenueBarChart({ data }: { data: RevenuJour[] }) {
  if (data.length === 0) return <div className="empty-state">Aucune donnée sur cette période</div>;
  const max = Math.max(...data.map((d) => d.total), 1);

  return (
    <div className="bar-chart" role="img" aria-label="Revenus par jour">
      {data.map((d) => (
        <div
          key={d.date}
          className="bar-chart-col"
          data-tooltip={`${new Date(d.date).toLocaleDateString()} : ${d.total.toFixed(2)}€`}
        >
          <div className="bar-chart-bar" style={{ height: `${Math.max(4, (d.total / max) * 100)}%` }} />
        </div>
      ))}
    </div>
  );
}

function TopArticlesChart({ data }: { data: ArticleVendu[] }) {
  if (data.length === 0) return <div className="empty-state">Aucune vente enregistrée</div>;
  const max = Math.max(...data.map((d) => d.quantite), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {data.map((d) => (
        <div key={d.nom}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
            <span>{d.nom}</span>
            <span className="muted">
              {d.quantite} vendu{d.quantite > 1 ? "s" : ""} — {d.total.toFixed(2)}€
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(d.quantite / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
