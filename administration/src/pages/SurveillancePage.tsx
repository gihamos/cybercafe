import { useCallback, useEffect, useState } from "react";
import { Eye, ExternalLink, Trash2, X } from "lucide-react";
import type { CSSProperties } from "react";
import { API_BASE_URL, api, getToken } from "../api/client";
import type { HistoriqueNavigationEntry, Poste, PosteScreenshotEntry } from "../api/types";

/** <img src> ne peut pas porter l'en-tête Authorization requis par l'API : on récupère
 * l'image en blob via fetch (comme downloadFile dans api/client.ts) puis on l'affiche
 * via une URL objet locale, révoquée au démontage. */
function AuthenticatedImage({ path, alt, style, onClick }: {
  path: string;
  alt: string;
  style?: CSSProperties;
  onClick?: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    const token = getToken();

    fetch(`${API_BASE_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => (res.ok ? res.blob() : Promise.reject(res)))
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (!url) {
    return <div style={{ ...style, background: "var(--surface-2)" }} />;
  }
  return <img src={url} alt={alt} style={style} onClick={onClick} />;
}

export default function SurveillancePage() {
  const [postes, setPostes] = useState<Poste[]>([]);
  const [posteId, setPosteId] = useState<number | null>(null);
  const [tab, setTab] = useState<"captures" | "historique">("captures");
  const [captures, setCaptures] = useState<PosteScreenshotEntry[]>([]);
  const [historique, setHistorique] = useState<HistoriqueNavigationEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [lightbox, setLightbox] = useState<PosteScreenshotEntry | null>(null);

  useEffect(() => {
    api.get<Poste[]>("/poste/").then((data) => {
      setPostes(data);
      if (data.length > 0) setPosteId(data[0].id);
    }).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    if (posteId === null) return;
    setLoading(true);
    try {
      if (tab === "captures") {
        setCaptures(await api.get<PosteScreenshotEntry[]>(`/surveillance/captures?poste_id=${posteId}`));
      } else {
        setHistorique(await api.get<HistoriqueNavigationEntry[]>(`/surveillance/historique?poste_id=${posteId}`));
      }
    } catch {
      // best-effort
    } finally {
      setLoading(false);
    }
  }, [posteId, tab]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(capture: PosteScreenshotEntry) {
    if (!confirm("Supprimer cette capture ?")) return;
    try {
      await api.delete(`/surveillance/captures/${capture.id}`);
      setCaptures((prev) => prev.filter((c) => c.id !== capture.id));
    } catch {
      alert("Erreur lors de la suppression");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Eye size={20} /> Surveillance
        </h1>
        <select value={posteId ?? ""} onChange={(e) => setPosteId(e.target.value ? Number(e.target.value) : null)}>
          {postes.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nom}
            </option>
          ))}
        </select>
      </div>
      <p className="muted">
        Captures d'écran périodiques et historique de navigation local des postes, collectés uniquement
        pendant les sessions actives — aucune interception réseau.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button className={`btn btn-sm ${tab === "captures" ? "btn-primary" : ""}`} onClick={() => setTab("captures")}>
          Captures d'écran
        </button>
        <button className={`btn btn-sm ${tab === "historique" ? "btn-primary" : ""}`} onClick={() => setTab("historique")}>
          Historique de navigation
        </button>
      </div>

      {loading && <p className="muted">Chargement...</p>}

      {!loading && tab === "captures" && (
        captures.length === 0 ? (
          <div className="card empty-state">Aucune capture pour ce poste.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
            {captures.map((c) => (
              <div key={c.id} className="card" style={{ padding: 8 }}>
                <AuthenticatedImage
                  path={`/surveillance/captures/${c.id}/image`}
                  alt={`Capture ${c.id}`}
                  style={{ width: "100%", height: 120, objectFit: "cover", borderRadius: 6, cursor: "pointer", display: "block" }}
                  onClick={() => setLightbox(c)}
                />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
                  <span className="muted" style={{ fontSize: 11 }}>
                    {new Date(c.date_capture).toLocaleString()}
                  </span>
                  <button className="btn btn-sm" onClick={() => handleDelete(c)} title="Supprimer">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {!loading && tab === "historique" && (
        <div className="card">
          {historique.length === 0 ? (
            <div className="empty-state">Aucune entrée d'historique pour ce poste.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Titre</th>
                  <th>URL</th>
                  <th>Navigateur</th>
                </tr>
              </thead>
              <tbody>
                {historique.map((h) => (
                  <tr key={h.id}>
                    <td>{new Date(h.date_visite).toLocaleString()}</td>
                    <td>{h.titre || "—"}</td>
                    <td>
                      <a href={h.url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        {h.url.length > 60 ? `${h.url.slice(0, 60)}...` : h.url} <ExternalLink size={12} />
                      </a>
                    </td>
                    <td>{h.navigateur || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {lightbox && (
        <div className="modal-overlay" onClick={() => setLightbox(null)}>
          <div style={{ position: "relative", maxWidth: "90vw", maxHeight: "90vh" }} onClick={(e) => e.stopPropagation()}>
            <AuthenticatedImage
              path={`/surveillance/captures/${lightbox.id}/image`}
              alt={`Capture ${lightbox.id}`}
              style={{ maxWidth: "90vw", maxHeight: "90vh", borderRadius: 8 }}
            />
            <button
              className="btn btn-sm"
              style={{ position: "absolute", top: 8, right: 8 }}
              onClick={() => setLightbox(null)}
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
