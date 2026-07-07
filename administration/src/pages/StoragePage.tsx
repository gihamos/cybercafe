import { useEffect, useRef, useState } from "react";
import { api, ApiError, downloadFile } from "../api/client";
import type { ClientUser, EquipeUser, FichierStocke, QuotaInfo } from "../api/types";
import { useAuth } from "../auth/AuthContext";

function humanSize(octets: number): string {
  const mo = octets / (1024 * 1024);
  return mo < 1 ? `${Math.round(octets / 1024)} Ko` : `${mo.toFixed(1)} Mo`;
}

export default function StoragePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <div className="page">
      <h1>Stockage</h1>
      <p className="muted">Espace de stockage réseau personnel, et gestion des quotas des comptes.</p>
      <MonEspace />
      {isAdmin && <QuotasUtilisateurs />}
    </div>
  );
}

function MonEspace() {
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [fichiers, setFichiers] = useState<FichierStocke[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    setError(null);
    try {
      const [q, f] = await Promise.all([
        api.get<QuotaInfo>("/stockage/quota"),
        api.get<FichierStocke[]>("/stockage/fichiers"),
      ]);
      setQuota(q);
      setFichiers(f);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.upload("/stockage/upload", file);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Échec de l'envoi");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDownload(f: FichierStocke) {
    try {
      await downloadFile(`/stockage/fichiers/${f.id}/download`, f.nom_original);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Échec du téléchargement");
    }
  }

  async function handleDelete(f: FichierStocke) {
    if (!confirm(`Supprimer « ${f.nom_original} » ?`)) return;
    try {
      await api.delete(`/stockage/fichiers/${f.id}`);
      setFichiers((prev) => prev.filter((x) => x.id !== f.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Échec de la suppression");
    }
  }

  const pct = quota && quota.quota_mo > 0 ? Math.min(100, (quota.usage_octets / (1024 * 1024) / quota.quota_mo) * 100) : 0;

  return (
    <div className="card">
      <div className="page-header">
        <h2>Mon espace de stockage</h2>
        <label className="btn btn-primary" style={{ cursor: "pointer" }}>
          {uploading ? "Envoi..." : "+ Envoyer un fichier"}
          <input ref={fileInputRef} type="file" style={{ display: "none" }} onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {error && <p className="error">{error}</p>}

      {quota && (
        <div style={{ margin: "12px 0" }}>
          <div className="hbar-track" style={{ height: 10 }}>
            <div className="hbar-fill" style={{ width: `${pct}%` }} />
          </div>
          <p className="muted" style={{ marginTop: 6 }}>
            {humanSize(quota.usage_octets)} utilisés sur {quota.quota_mo.toFixed(0)} Mo
          </p>
        </div>
      )}

      {fichiers.length === 0 ? (
        <div className="empty-state">Aucun fichier</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Taille</th>
              <th>Envoyé le</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {fichiers.map((f) => (
              <tr key={f.id}>
                <td>{f.nom_original}</td>
                <td className="muted">{humanSize(f.taille_octets)}</td>
                <td className="muted">{new Date(f.date_upload).toLocaleString()}</td>
                <td>
                  <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                    <button className="btn btn-sm" onClick={() => handleDownload(f)}>Télécharger</button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(f)}>Supprimer</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function QuotasUtilisateurs() {
  const [users, setUsers] = useState<(ClientUser | EquipeUser)[]>([]);
  const [quotas, setQuotas] = useState<Record<number, QuotaInfo>>({});
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<ClientUser[]>("/user/clients"),
      api.get<EquipeUser[]>("/user/equipe"),
    ])
      .then(([clients, equipe]) => setUsers([...clients, ...equipe]))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"));
  }, []);

  useEffect(() => {
    if (users.length === 0) return;
    let cancelled = false;
    (async () => {
      for (const u of users) {
        if (cancelled) return;
        try {
          const q = await api.get<QuotaInfo>(`/stockage/quota/${u.id}`);
          if (!cancelled) setQuotas((prev) => ({ ...prev, [u.id]: q }));
        } catch {
          // ignoré : cette ligne affichera "..." en continu
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [users]);

  async function handleSave(userId: number) {
    const raw = editing[userId];
    const quota_stockage_mo = raw === "" || raw === undefined ? null : Number(raw);
    try {
      await api.patch(`/stockage/quota/${userId}`, { quota_stockage_mo });
      const q = await api.get<QuotaInfo>(`/stockage/quota/${userId}`);
      setQuotas((prev) => ({ ...prev, [userId]: q }));
      setEditing((prev) => {
        const next = { ...prev };
        delete next[userId];
        return next;
      });
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Échec de l'enregistrement");
    }
  }

  const filtered = users.filter((u) => u.username.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="card">
      <h2>Quotas des utilisateurs</h2>
      {error && <p className="error">{error}</p>}
      <input
        placeholder="Rechercher un utilisateur..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ marginBottom: 12, width: 280 }}
      />
      <table>
        <thead>
          <tr>
            <th>Utilisateur</th>
            <th>Utilisation</th>
            <th>Quota (Mo)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filtered.slice(0, 30).map((u) => {
            const q = quotas[u.id];
            return (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td className="muted">{q ? humanSize(q.usage_octets) : "..."}</td>
                <td>
                  <input
                    style={{ width: 90 }}
                    placeholder={q ? String(q.quota_mo) : "..."}
                    value={editing[u.id] ?? ""}
                    onChange={(e) => setEditing((prev) => ({ ...prev, [u.id]: e.target.value }))}
                  />
                </td>
                <td>
                  <button className="btn btn-sm" onClick={() => handleSave(u.id)}>Enregistrer</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
