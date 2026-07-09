import { useCallback, useEffect, useState } from "react";
import { BarChart3, Download, TrendingUp, TrendingDown } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { StatsDetaille } from "../api/types";

type Preset = "7j" | "30j" | "90j" | "mois" | "custom";

function presetToRange(preset: Preset): { debut: Date; fin: Date } {
  const fin = new Date();
  const debut = new Date();
  if (preset === "7j") debut.setDate(fin.getDate() - 7);
  else if (preset === "30j") debut.setDate(fin.getDate() - 30);
  else if (preset === "90j") debut.setDate(fin.getDate() - 90);
  else if (preset === "mois") debut.setDate(1);
  return { debut, fin };
}

function toInputDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export default function StatistiquesPage() {
  const [preset, setPreset] = useState<Preset>("30j");
  const [debut, setDebut] = useState(toInputDate(presetToRange("30j").debut));
  const [fin, setFin] = useState(toInputDate(presetToRange("30j").fin));
  const [stats, setStats] = useState<StatsDetaille | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (d: string, f: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        date_debut: new Date(d).toISOString(),
        date_fin: new Date(f + "T23:59:59").toISOString(),
      });
      const data = await api.get<StatsDetaille>(`/stats/detaille?${params}`);
      setStats(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(debut, fin);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyPreset(p: Preset) {
    setPreset(p);
    if (p === "custom") return;
    const range = presetToRange(p);
    const d = toInputDate(range.debut);
    const f = toInputDate(range.fin);
    setDebut(d);
    setFin(f);
    load(d, f);
  }

  function handleCustomChange(which: "debut" | "fin", value: string) {
    setPreset("custom");
    if (which === "debut") setDebut(value);
    else setFin(value);
  }

  function handleApplyCustom() {
    load(debut, fin);
  }

  function handleExportCsv() {
    if (!stats) return;
    const rows: string[][] = [
      ["Section", "Clé", "Quantité/Nb", "Montant (€)"],
      ...stats.revenus_par_jour.map((r) => ["Revenus par jour", r.date, "", r.total.toFixed(2)]),
      ...stats.ventes_par_categorie.map((v) => ["Ventes par catégorie", v.nom, String(v.quantite), v.total.toFixed(2)]),
      ...stats.usage_par_poste.map((u) => ["Usage par poste", u.poste_nom, String(u.nb_sessions), String(u.minutes_totales)]),
      ...stats.clients_par_groupe.map((g) => ["Clients par groupe", g.nom, String(g.nb_clients), g.revenu.toFixed(2)]),
    ];
    const csv = rows.map((r) => r.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `statistiques_${debut}_${fin}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <BarChart3 size={20} /> Statistiques
        </h1>
        <button className="btn" onClick={handleExportCsv} disabled={!stats}>
          <Download size={15} /> Exporter en CSV
        </button>
      </div>

      <div className="card" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div className="view-toggle">
          {(["7j", "30j", "90j", "mois"] as Preset[]).map((p) => (
            <button key={p} className={preset === p ? "active" : ""} onClick={() => applyPreset(p)}>
              {p === "7j" ? "7 jours" : p === "30j" ? "30 jours" : p === "90j" ? "90 jours" : "Ce mois"}
            </button>
          ))}
        </div>
        <span className="muted">ou période personnalisée :</span>
        <input type="date" value={debut} onChange={(e) => handleCustomChange("debut", e.target.value)} />
        <span className="muted">→</span>
        <input type="date" value={fin} onChange={(e) => handleCustomChange("fin", e.target.value)} />
        <button className="btn btn-sm" onClick={handleApplyCustom}>
          Appliquer
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Chargement...</p>}

      {stats && (
        <>
          <div className="stat-tiles">
            <div className="stat-tile">
              <span className="stat-tile-label">Revenu de la période</span>
              <span className="stat-tile-value">{stats.revenu_total.toFixed(2)}€</span>
              {stats.variation_pct !== null && (
                <span
                  className="stat-tile-sub"
                  style={{ color: stats.variation_pct >= 0 ? "var(--good)" : "var(--critical)", display: "flex", alignItems: "center", gap: 4 }}
                >
                  {stats.variation_pct >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                  {Math.abs(stats.variation_pct)}% vs période précédente
                </span>
              )}
            </div>
            <div className="stat-tile">
              <span className="stat-tile-label">Nouveaux clients</span>
              <span className="stat-tile-value">{stats.nouveaux_clients}</span>
            </div>
            <div className="stat-tile">
              <span className="stat-tile-label">Revenu période précédente</span>
              <span className="stat-tile-value">{stats.revenu_periode_precedente.toFixed(2)}€</span>
            </div>
          </div>

          <div className="card">
            <h2>Revenus par jour</h2>
            <RevenueBarChart data={stats.revenus_par_jour} />
          </div>

          <div className="card">
            <h2>Ventes par catégorie</h2>
            <CategorieChart data={stats.ventes_par_categorie} />
          </div>

          <div className="card">
            <h2>Utilisation par poste</h2>
            <PosteChart data={stats.usage_par_poste} />
          </div>

          <div className="card">
            <h2>Revenu par groupe de clients</h2>
            <GroupeChart data={stats.clients_par_groupe} />
          </div>
        </>
      )}
    </div>
  );
}

function RevenueBarChart({ data }: { data: StatsDetaille["revenus_par_jour"] }) {
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

function CategorieChart({ data }: { data: StatsDetaille["ventes_par_categorie"] }) {
  if (data.length === 0) return <div className="empty-state">Aucune vente sur cette période</div>;
  const max = Math.max(...data.map((d) => d.total), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {data.map((d) => (
        <div key={d.categorie_id}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
            <span>
              {d.emoji} {d.nom}
            </span>
            <span className="muted">
              {d.quantite} vendu{d.quantite > 1 ? "s" : ""} — {d.total.toFixed(2)}€
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(d.total / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function PosteChart({ data }: { data: StatsDetaille["usage_par_poste"] }) {
  if (data.length === 0) return <div className="empty-state">Aucune session sur cette période</div>;
  const max = Math.max(...data.map((d) => d.minutes_totales), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {data.map((d) => (
        <div key={d.poste_id}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
            <span>{d.poste_nom}</span>
            <span className="muted">
              {d.nb_sessions} session{d.nb_sessions > 1 ? "s" : ""} — {d.minutes_totales} min
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(d.minutes_totales / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function GroupeChart({ data }: { data: StatsDetaille["clients_par_groupe"] }) {
  if (data.length === 0) return <div className="empty-state">Aucun groupe</div>;
  const max = Math.max(...data.map((d) => d.revenu), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {data.map((d) => (
        <div key={d.groupe_id ?? "sans-groupe"}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
            <span>{d.nom}</span>
            <span className="muted">
              {d.nb_clients} client{d.nb_clients > 1 ? "s" : ""} — {d.revenu.toFixed(2)}€
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(d.revenu / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
