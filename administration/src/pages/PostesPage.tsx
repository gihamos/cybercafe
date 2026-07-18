import { useCallback, useEffect, useState } from "react";
import type { CSSProperties, FormEvent } from "react";
import { HardDriveDownload, KeyRound, LayoutGrid, List, Lock, Pencil, Power, RotateCw, ShieldQuestion, Unlock, Zap, Trash2, Wifi, WifiOff, Monitor } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
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

const ETAT_COLOR_VAR: Record<PosteEtat, string> = {
  libre: "var(--good)",
  occupe: "var(--warning)",
  bloque: "var(--text-muted)",
  hors_ligne: "var(--critical)",
};

interface CreatePosteResult extends Poste {
  token: string;
}

type ViewMode = "grid" | "table";

export default function PostesPage() {
  const { isAdmin, hasPermission } = usePermissions();
  const peutGererPostes = hasPermission("postes");
  const [postes, setPostes] = useState<Poste[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Poste | null>(null);
  const [newToken, setNewToken] = useState<{ nom: string; token: string } | null>(null);
  const [codeSecours, setCodeSecours] = useState<{ nom: string; code: string; expire_le: string; transmis_au_poste: boolean } | null>(null);
  const [view, setView] = useState<ViewMode>("grid");

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

  async function handleReveiller(id: number) {
    try {
      await api.post(`/poste/${id}/reveil`);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDesactiverKiosque(id: number, nom: string) {
    if (!confirm(`Désactiver le kiosk sur « ${nom} » ? Le logiciel client se fermera immédiatement sur ce poste.`)) return;
    try {
      await api.post(`/poste/${id}/desactiver-kiosque`);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleRedemarrer(id: number, nom: string) {
    if (!confirm(`Redémarrer le poste « ${nom} » ? Toute session en cours sera interrompue.`)) return;
    try {
      await api.post(`/poste/${id}/commande?commande=redemarrer`);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleEteindre(id: number, nom: string) {
    if (!confirm(`Éteindre le poste « ${nom} » ? Toute session en cours sera interrompue.`)) return;
    try {
      await api.post(`/poste/${id}/commande?commande=eteindre`);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleVerrouillerLecteur(id: number, nom: string) {
    const identifiant = prompt(
      `Lettre du lecteur à verrouiller sur « ${nom} » (ex: E) — ou point de montage sur Linux :`
    );
    if (!identifiant) return;
    try {
      await api.post(`/poste/${id}/commande?commande=verrouiller_lecteur`, { identifiant });
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleGenererCodeSecours(id: number, nom: string) {
    try {
      const result = await api.post<{ code: string; expire_le: string; transmis_au_poste: boolean }>(
        `/poste/${id}/code-secours`
      );
      setCodeSecours({ nom, ...result });
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

  async function handleRegenererToken(id: number, nom: string) {
    if (!confirm(`Régénérer le token du poste « ${nom} » ? L'ancien token cessera immédiatement de fonctionner.`)) return;
    try {
      const result = await api.post<CreatePosteResult>(`/poste/${id}/regenerer-token`);
      const { token, ...poste } = result;
      setPostes((prev) => prev.map((p) => (p.id === id ? poste : p)));
      setNewToken({ nom: poste.nom, token });
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  const compteParEtat = postes.reduce<Record<string, number>>((acc, p) => {
    acc[p.etat] = (acc[p.etat] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Monitor size={20} /> Postes
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className={`badge ${connected ? "badge-success" : "badge-neutral"}`}>
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {connected ? "Temps réel actif" : "Connexion..."}
          </span>
          <div className="view-toggle">
            <button className={view === "grid" ? "active" : ""} onClick={() => setView("grid")}>
              <LayoutGrid size={14} /> Grille
            </button>
            <button className={view === "table" ? "active" : ""} onClick={() => setView("table")}>
              <List size={14} /> Tableau
            </button>
          </div>
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              + Nouveau poste
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        {(Object.keys(ETAT_LABELS) as PosteEtat[]).map((etat) => (
          <span key={etat} className={`badge ${ETAT_BADGE[etat]}`}>
            <span className="badge-dot" /> {compteParEtat[etat] || 0} {ETAT_LABELS[etat].toLowerCase()}
          </span>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Chargement...</p>
      ) : postes.length === 0 ? (
        <div className="card">
          <div className="empty-state">Aucun poste enregistré</div>
        </div>
      ) : view === "grid" ? (
        <div className="tile-grid">
          {postes.map((p) => {
            const session = p.session_active;
            const pct = session?.limite_minutes
              ? Math.min(100, ((session.consommation_minutes || 0) / session.limite_minutes) * 100)
              : null;
            return (
              <div key={p.id} className="poste-tile" style={{ "--tile-color": ETAT_COLOR_VAR[p.etat] } as CSSProperties}>
                <div className="poste-tile-head">
                  <div>
                    <div className="poste-tile-name">{p.nom}</div>
                    <span className={`badge ${ETAT_BADGE[p.etat]}`} style={{ marginTop: 4 }}>
                      {ETAT_LABELS[p.etat]}
                    </span>
                  </div>
                  <span className="poste-tile-dot" />
                </div>

                <div className="poste-tile-meta">
                  <span>{p.est_en_ligne ? "En ligne" : "Hors ligne"} · {p.hostname || "—"}</span>
                  <span className="muted" style={{ fontSize: 12 }}>
                    {p.ip || "IP inconnue"} · {p.mac_adresse || "MAC inconnue"}
                  </span>
                  {session && (
                    <span>
                      {session.limite_minutes
                        ? `${session.consommation_minutes}/${session.limite_minutes} min`
                        : "Temps illimité"}
                    </span>
                  )}
                </div>

                {pct !== null && (
                  <div className="poste-tile-progress">
                    <div className="poste-tile-progress-fill" style={{ width: `${pct}%` }} />
                  </div>
                )}

                {peutGererPostes && (
                  <div className="poste-tile-actions" style={{ flexWrap: "wrap" }}>
                    {!p.est_en_ligne && p.mac_adresse ? (
                      <button className="btn btn-sm" onClick={() => handleReveiller(p.id)}>
                        <Zap size={13} /> Réveiller
                      </button>
                    ) : p.est_verrouille ? (
                      <button className="btn btn-sm" onClick={() => handleDeverrouiller(p.id)}>
                        <Unlock size={13} /> Déverrouiller
                      </button>
                    ) : (
                      <button className="btn btn-sm" onClick={() => handleVerrouiller(p.id)}>
                        <Lock size={13} /> Verrouiller
                      </button>
                    )}
                    <button className="btn btn-sm" onClick={() => setEditing(p)}>
                      <Pencil size={13} /> Modifier
                    </button>
                    <button className="btn btn-sm" onClick={() => handleGenererCodeSecours(p.id, p.nom)}>
                      <ShieldQuestion size={13} /> Code de secours
                    </button>
                    {p.est_en_ligne && (
                      <>
                        <button className="btn btn-sm" onClick={() => handleVerrouillerLecteur(p.id, p.nom)}>
                          <HardDriveDownload size={13} /> Verrouiller un lecteur
                        </button>
                        <button className="btn btn-sm" onClick={() => handleRedemarrer(p.id, p.nom)}>
                          <RotateCw size={13} /> Redémarrer
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleEteindre(p.id, p.nom)}>
                          <Power size={13} /> Éteindre
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDesactiverKiosque(p.id, p.nom)}>
                          <Power size={13} /> Désactiver le kiosk
                        </button>
                      </>
                    )}
                    {isAdmin && (
                      <>
                        <button className="btn btn-sm" onClick={() => handleRegenererToken(p.id, p.nom)}>
                          <KeyRound size={13} /> Régénérer le token
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p.id, p.nom)}>
                          <Trash2 size={13} /> Supprimer
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>État</th>
                <th>Connexion</th>
                <th>IP</th>
                <th>MAC</th>
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
                  <td className="muted">{p.ip || "—"}</td>
                  <td className="muted">{p.mac_adresse || "—"}</td>
                  <td className="muted">{new Date(p.derniere_activite).toLocaleString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      {peutGererPostes && !p.est_en_ligne && p.mac_adresse && (
                        <button className="btn btn-sm" onClick={() => handleReveiller(p.id)}>
                          <Zap size={13} /> Réveiller
                        </button>
                      )}
                      {peutGererPostes && (
                        <button className="btn btn-sm" title="Code de secours" onClick={() => handleGenererCodeSecours(p.id, p.nom)}>
                          <ShieldQuestion size={13} />
                        </button>
                      )}
                      {peutGererPostes && p.est_en_ligne && (
                        <>
                          <button className="btn btn-sm" title="Verrouiller un lecteur" onClick={() => handleVerrouillerLecteur(p.id, p.nom)}>
                            <HardDriveDownload size={13} />
                          </button>
                          <button className="btn btn-sm" title="Redémarrer" onClick={() => handleRedemarrer(p.id, p.nom)}>
                            <RotateCw size={13} />
                          </button>
                          <button className="btn btn-sm btn-danger" title="Éteindre" onClick={() => handleEteindre(p.id, p.nom)}>
                            <Power size={13} />
                          </button>
                          <button className="btn btn-sm btn-danger" title="Désactiver le kiosk" onClick={() => handleDesactiverKiosque(p.id, p.nom)}>
                            <Power size={13} />
                          </button>
                        </>
                      )}
                      {peutGererPostes && (
                        p.est_verrouille ? (
                          <button className="btn btn-sm" onClick={() => handleDeverrouiller(p.id)}>
                            Déverrouiller
                          </button>
                        ) : (
                          <button className="btn btn-sm" onClick={() => handleVerrouiller(p.id)}>
                            Verrouiller
                          </button>
                        )
                      )}
                      {peutGererPostes && (
                        <button className="btn btn-sm" title="Modifier" onClick={() => setEditing(p)}>
                          <Pencil size={13} />
                        </button>
                      )}
                      {isAdmin && (
                        <button className="btn btn-sm" title="Régénérer le token" onClick={() => handleRegenererToken(p.id, p.nom)}>
                          <KeyRound size={13} />
                        </button>
                      )}
                      {isAdmin && (
                        <button className="btn btn-sm btn-danger" title="Supprimer" onClick={() => handleDelete(p.id, p.nom)}>
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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

      {editing && (
        <EditPosteModal
          poste={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setPostes((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
            setEditing(null);
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
              background: "var(--surface-2)",
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

      {codeSecours && (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <h3>Code de secours « {codeSecours.nom} »</h3>
          <p className="muted">
            À communiquer immédiatement par téléphone à la personne présente sur le poste (menu admin local,
            raccourci Ctrl+Alt+Maj+Q). Usage unique, valable jusqu'à {new Date(codeSecours.expire_le).toLocaleTimeString()}.
            {!codeSecours.transmis_au_poste && (
              <> Le poste est actuellement hors ligne : le code ne fonctionnera que s'il se reconnecte avant expiration.</>
            )}
          </p>
          <code
            style={{
              display: "block",
              padding: 10,
              background: "var(--surface-2)",
              borderRadius: 6,
              wordBreak: "break-all",
              fontSize: 18,
              letterSpacing: 1,
            }}
          >
            {codeSecours.code}
          </code>
          <button className="btn btn-sm" style={{ marginTop: 10 }} onClick={() => setCodeSecours(null)}>
            J'ai transmis le code
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
  const [macAdresse, setMacAdresse] = useState("");
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
        mac_adresse: macAdresse || null,
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
          Adresse MAC (pour le réveil à distance)
          <input value={macAdresse} onChange={(e) => setMacAdresse(e.target.value)} placeholder="AA:BB:CC:DD:EE:FF" />
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

function EditPosteModal({
  poste,
  onClose,
  onSaved,
}: {
  poste: Poste;
  onClose: () => void;
  onSaved: (poste: Poste) => void;
}) {
  const [nom, setNom] = useState(poste.nom);
  const [description, setDescription] = useState(poste.description || "");
  const [typePoste, setTypePoste] = useState<TypePoste>(poste.type_poste);
  const [macAdresse, setMacAdresse] = useState(poste.mac_adresse || "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const updated = await api.patch<Poste>(`/poste/${poste.id}`, {
        nom,
        description: description || null,
        type_poste: typePoste,
        mac_adresse: macAdresse || null,
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la modification");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Modifier le poste</h2>
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
          Adresse MAC (pour le réveil à distance)
          <input value={macAdresse} onChange={(e) => setMacAdresse(e.target.value)} placeholder="AA:BB:CC:DD:EE:FF" />
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
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
