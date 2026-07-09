import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Tags, Plus, Trash2, Gauge, ShieldBan } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { BandePassanteProfil, SiteRegleEntry, UserGroupEntry } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export default function UserGroupsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [groups, setGroups] = useState<UserGroupEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [limitsTarget, setLimitsTarget] = useState<UserGroupEntry | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<UserGroupEntry[]>("/user-group/");
      setGroups(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(g: UserGroupEntry) {
    if (!confirm(`Supprimer le groupe « ${g.nom} » ? Les membres ne seront pas supprimés.`)) return;
    try {
      await api.delete(`/user-group/${g.id}`);
      setGroups((prev) => prev.filter((x) => x.id !== g.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Échec de la suppression");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Tags size={20} /> Groupes de clients
        </h1>
        {isAdmin && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={15} /> Nouveau groupe
          </button>
        )}
      </div>
      <p className="page-subtitle">
        Organisez vos clients par groupe (VIP, étudiants, scolaire...) — filtrable depuis la fiche client.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : groups.length === 0 ? (
          <div className="empty-state">Aucun groupe créé</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>Description</th>
                <th>Membres</th>
                <th>Créé le</th>
                {isAdmin && <th></th>}
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <tr key={g.id}>
                  <td>
                    <strong>{g.nom}</strong>
                  </td>
                  <td className="muted">{g.description || "—"}</td>
                  <td>
                    <span className="badge badge-accent">{g.nb_membres}</span>
                  </td>
                  <td className="muted">{new Date(g.date_creation).toLocaleDateString()}</td>
                  {isAdmin && (
                    <td>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn-sm" onClick={() => setLimitsTarget(g)}>
                          <Gauge size={13} /> Limites
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(g)}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateGroupModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}

      {limitsTarget && (
        <GroupLimitsModal groupe={limitsTarget} onClose={() => setLimitsTarget(null)} />
      )}
    </div>
  );
}

function GroupLimitsModal({ groupe, onClose }: { groupe: UserGroupEntry; onClose: () => void }) {
  const [profil, setProfil] = useState<BandePassanteProfil | null>(null);
  const [download, setDownload] = useState("");
  const [upload, setUpload] = useState("");
  const [quotaJour, setQuotaJour] = useState("");
  const [regles, setRegles] = useState<SiteRegleEntry[]>([]);
  const [nouveauDomaine, setNouveauDomaine] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [bp, sites] = await Promise.all([
        api.get<BandePassanteProfil | null>(`/bande-passante/profils/applicable?groupe_id=${groupe.id}`),
        api.get<SiteRegleEntry[]>(`/site-regle/?groupe_id=${groupe.id}`),
      ]);
      if (bp && bp.type_profil === "groupe" && bp.groupe_id === groupe.id) {
        setProfil(bp);
        setDownload(bp.download_mbps != null ? String(bp.download_mbps) : "");
        setUpload(bp.upload_mbps != null ? String(bp.upload_mbps) : "");
        setQuotaJour(bp.quota_journalier_mo != null ? String(bp.quota_journalier_mo) : "");
      }
      setRegles(sites);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSaveBandwidth(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.post<BandePassanteProfil>("/bande-passante/profils", {
        type_profil: "groupe",
        groupe_id: groupe.id,
        download_mbps: download ? parseFloat(download) : null,
        upload_mbps: upload ? parseFloat(upload) : null,
        quota_journalier_mo: quotaJour ? parseFloat(quotaJour) : null,
        bloquer_si_depasse: !!quotaJour,
      });
      setProfil(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveBandwidth() {
    if (!profil) return;
    if (!confirm("Retirer la limite de bande passante de ce groupe ?")) return;
    try {
      await api.delete(`/bande-passante/profils/${profil.id}`);
      setProfil(null);
      setDownload("");
      setUpload("");
      setQuotaJour("");
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleAddDomaine(e: FormEvent) {
    e.preventDefault();
    if (!nouveauDomaine.trim()) return;
    try {
      const regle = await api.post<SiteRegleEntry>("/site-regle/", {
        domaine: nouveauDomaine.trim(),
        groupe_id: groupe.id,
      });
      setRegles((prev) => [...prev, regle]);
      setNouveauDomaine("");
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleRemoveDomaine(r: SiteRegleEntry) {
    try {
      await api.delete(`/site-regle/${r.id}`);
      setRegles((prev) => prev.filter((x) => x.id !== r.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  const reglesGlobales = regles.filter((r) => r.groupe_id === null);
  const reglesGroupe = regles.filter((r) => r.groupe_id === groupe.id);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} style={{ width: 460 }}>
        <h2>Limites du groupe « {groupe.nom} »</h2>
        {error && <p className="error">{error}</p>}
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : (
          <>
            <section>
              <h3 style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Gauge size={15} /> Bande passante
              </h3>
              <form onSubmit={handleSaveBandwidth} className="form-grid" style={{ marginTop: 8 }}>
                <label>
                  Débit descendant (Mbps)
                  <input type="number" step="0.1" min="0" value={download} onChange={(e) => setDownload(e.target.value)} />
                </label>
                <label>
                  Débit montant (Mbps)
                  <input type="number" step="0.1" min="0" value={upload} onChange={(e) => setUpload(e.target.value)} />
                </label>
                <label>
                  Quota journalier (Mo)
                  <input type="number" step="1" min="0" value={quotaJour} onChange={(e) => setQuotaJour(e.target.value)} />
                </label>
                <div style={{ display: "flex", alignItems: "flex-end", gap: 6 }}>
                  <button type="submit" className="btn btn-sm btn-primary" disabled={saving}>
                    Enregistrer
                  </button>
                  {profil && (
                    <button type="button" className="btn btn-sm btn-danger" onClick={handleRemoveBandwidth}>
                      Retirer
                    </button>
                  )}
                </div>
              </form>
            </section>

            <section style={{ marginTop: 18 }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <ShieldBan size={15} /> Filtrage de contenu
              </h3>
              <p className="muted" style={{ marginTop: 4 }}>
                Domaines bloqués sur les postes lorsqu'un client de ce groupe est connecté (en plus des règles
                globales).
              </p>

              {reglesGlobales.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <span className="section-title">Règles globales (tous les clients)</span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                    {reglesGlobales.map((r) => (
                      <span key={r.id} className="badge badge-neutral">
                        {r.domaine}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                {reglesGroupe.length === 0 && <p className="muted">Aucun site bloqué spécifique à ce groupe</p>}
                {reglesGroupe.map((r) => (
                  <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span>{r.domaine}</span>
                    <button className="btn btn-sm btn-danger" onClick={() => handleRemoveDomaine(r)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>

              <form onSubmit={handleAddDomaine} style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <input
                  style={{ flex: 1 }}
                  placeholder="exemple.com"
                  value={nouveauDomaine}
                  onChange={(e) => setNouveauDomaine(e.target.value)}
                />
                <button type="submit" className="btn btn-sm">
                  <Plus size={13} /> Bloquer
                </button>
              </form>
            </section>
          </>
        )}

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

function CreateGroupModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [nom, setNom] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/user-group/", { nom, description: description || null });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouveau groupe</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom
          <input value={nom} onChange={(e) => setNom(e.target.value)} required autoFocus />
        </label>
        <label>
          Description
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
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
