import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Poste, PosteEtat, TypePoste } from "../api/types";
import { useAdminSocket } from "../ws/useAdminSocket";

const ETAT_LABELS: Record<PosteEtat, string> = {
  libre: "Libre",
  occupe: "Occupé",
  bloque: "Bloqué",
  hors_ligne: "Hors ligne",
};

const ETAT_BADGE: Record<PosteEtat, string> = {
  libre: "badge-success",
  occupe: "badge-warning",
  bloque: "badge-neutral",
  hors_ligne: "badge-danger",
};

interface CreatePosteResult extends Poste {
  token: string;
}

export default function PostesPage() {
  const [postes, setPostes] = useState<Poste[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newToken, setNewToken] = useState<{ nom: string; token: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Poste[]>("/poste/");
      setPostes(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const { connected } = useAdminSocket(
    useCallback((msg) => {
      if (msg.type === "poste_updated") {
        setPostes((prev) => {
          const exists = prev.some((p) => p.id === msg.data.id);
          if (!exists) return prev;
          return prev.map((p) => (p.id === msg.data.id ? { ...p, ...msg.data } : p));
        });
      }
    }, [])
  );

  async function handleVerrouiller(id: number) {
    try {
      const updated = await api.patch<Poste>(`/poste/${id}/verrouiller`);
      setPostes((prev) => prev.map((p) => (p.id === id ? updated : p)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDeverrouiller(id: number) {
    try {
      const updated = await api.patch<Poste>(`/poste/${id}/deverrouiller`);
      setPostes((prev) => prev.map((p) => (p.id === id ? updated : p)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDelete(id: number, nom: string) {
    if (!confirm(`Supprimer le poste « ${nom} » ?`)) return;
    try {
      await api.delete(`/poste/${id}`);
      setPostes((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Postes</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className={`badge ${connected ? "badge-success" : "badge-neutral"}`}>
            {connected ? "Temps réel actif" : "Connexion..."}
          </span>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + Nouveau poste
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : postes.length === 0 ? (
          <div className="empty-state">Aucun poste enregistré</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>État</th>
                <th>Connexion</th>
                <th>Dernière activité</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {postes.map((p) => (
                <tr key={p.id}>
                  <td>
                    <strong>{p.nom}</strong>
                    {p.description && <div className="muted">{p.description}</div>}
                  </td>
                  <td>
                    <span className={`badge ${ETAT_BADGE[p.etat]}`}>{ETAT_LABELS[p.etat]}</span>
                  </td>
                  <td>
                    <span className={`badge ${p.est_en_ligne ? "badge-success" : "badge-danger"}`}>
                      {p.est_en_ligne ? "En ligne" : "Hors ligne"}
                    </span>
                  </td>
                  <td className="muted">{new Date(p.derniere_activite).toLocaleString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      {p.est_verrouille ? (
                        <button className="btn btn-sm" onClick={() => handleDeverrouiller(p.id)}>
                          Déverrouiller
                        </button>
                      ) : (
                        <button className="btn btn-sm" onClick={() => handleVerrouiller(p.id)}>
                          Verrouiller
                        </button>
                      )}
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p.id, p.nom)}>
                        Supprimer
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreatePosteModal
          onClose={() => setShowCreate(false)}
          onCreated={(poste, token) => {
            setPostes((prev) => [...prev, poste]);
            setNewToken({ nom: poste.nom, token });
            setShowCreate(false);
          }}
        />
      )}

      {newToken && (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <h3>Token du poste « {newToken.nom} »</h3>
          <p className="muted">
            À saisir une seule fois dans le client desktop du poste (voir client/README.md). Il ne sera plus
            jamais réaffiché — pensez à le noter maintenant.
          </p>
          <code
            style={{
              display: "block",
              padding: 10,
              background: "var(--bg)",
              borderRadius: 6,
              wordBreak: "break-all",
            }}
          >
            {newToken.token}
          </code>
          <button className="btn btn-sm" style={{ marginTop: 10 }} onClick={() => setNewToken(null)}>
            J'ai noté le token
          </button>
        </div>
      )}
    </div>
  );
}

function CreatePosteModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (poste: Poste, token: string) => void;
}) {
  const [nom, setNom] = useState("");
  const [description, setDescription] = useState("");
  const [typePoste, setTypePoste] = useState<TypePoste>("client");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const result = await api.post<CreatePosteResult>("/poste/", {
        nom,
        description: description || null,
        type_poste: typePoste,
      });
      const { token, ...poste } = result;
      onCreated(poste, token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouveau poste</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom
          <input value={nom} onChange={(e) => setNom(e.target.value)} required autoFocus />
        </label>
        <label>
          Description
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label>
          Type
          <select value={typePoste} onChange={(e) => setTypePoste(e.target.value as TypePoste)}>
            <option value="client">Client</option>
            <option value="admin">Admin</option>
            <option value="serveur">Serveur</option>
            <option value="borne_wifi">Borne wifi</option>
          </select>
        </label>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Création..." : "Créer"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
