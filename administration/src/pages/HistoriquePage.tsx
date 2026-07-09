import { useCallback, useEffect, useState } from "react";
import { History } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { HistoriqueEntry } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export default function HistoriquePage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<HistoriqueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userIdFilter, setUserIdFilter] = useState("");
  const [posteIdFilter, setPosteIdFilter] = useState("");

  const load = useCallback(async (userId: string, posteId: string) => {
    setLoading(true);
    setError(null);
    try {
      let path = "/historique/?limit=100";
      if (userId) path = `/historique/user/${userId}?limit=100`;
      else if (posteId) path = `/historique/poste/${posteId}?limit=100`;

      const data = await api.get<HistoriqueEntry[]>(path);
      setEntries(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(userIdFilter, posteIdFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilter() {
    load(userIdFilter, posteIdFilter);
  }

  async function handlePurge() {
    const days = prompt("Supprimer les entrées plus vieilles que combien de jours ?", "90");
    if (!days) return;
    try {
      const result = await api.delete<{ supprimes: number }>(`/historique/purge?days=${encodeURIComponent(days)}`);
      alert(`${result.supprimes} entrées supprimées.`);
      load(userIdFilter, posteIdFilter);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <History size={20} /> Historique
        </h1>
        {user?.role === "admin" && (
          <button className="btn btn-danger" onClick={handlePurge}>
            Purger les anciens logs
          </button>
        )}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          placeholder="Filtrer par user_id"
          value={userIdFilter}
          onChange={(e) => { setUserIdFilter(e.target.value); setPosteIdFilter(""); }}
          style={{ maxWidth: 180 }}
        />
        <input
          placeholder="Filtrer par poste_id"
          value={posteIdFilter}
          onChange={(e) => { setPosteIdFilter(e.target.value); setUserIdFilter(""); }}
          style={{ maxWidth: 180 }}
        />
        <button className="btn" onClick={handleFilter}>
          Filtrer
        </button>
        {(userIdFilter || posteIdFilter) && (
          <button
            className="btn"
            onClick={() => {
              setUserIdFilter("");
              setPosteIdFilter("");
              load("", "");
            }}
          >
            Réinitialiser
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : entries.length === 0 ? (
          <div className="empty-state">Aucune entrée</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Événement</th>
                <th>Description</th>
                <th>Contexte</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td className="muted">{new Date(e.timestamp).toLocaleString()}</td>
                  <td>
                    <span className="badge badge-neutral">{e.type_evenement}</span>
                  </td>
                  <td>{e.description}</td>
                  <td className="muted">
                    {e.user_id ? `user #${e.user_id} ` : ""}
                    {e.poste_id ? `poste #${e.poste_id} ` : ""}
                    {e.ticket_id ? `ticket #${e.ticket_id}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
