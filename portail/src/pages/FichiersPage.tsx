import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FolderOpen, Trash2, Upload } from "lucide-react";
import { api, ApiError, downloadFile } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";
import type { FichierStocke } from "../api/types";

function formatTaille(octets: number): string {
  if (octets >= 1024 * 1024) return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
  if (octets >= 1024) return `${(octets / 1024).toFixed(0)} Ko`;
  return `${octets} o`;
}

export default function FichiersPage() {
  const { profil, rechargerProfil } = usePortalAuth();
  const [fichiers, setFichiers] = useState<FichierStocke[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const charger = useCallback(async () => {
    try {
      setFichiers(await api.get<FichierStocke[]>("/stockage/fichiers"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    }
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  async function handleUpload(file: File) {
    setError(null);
    setUploading(true);
    try {
      await api.upload("/stockage/upload", file);
      await charger();
      await rechargerProfil();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleDelete(f: FichierStocke) {
    if (!confirm(`Supprimer « ${f.nom_original} » ?`)) return;
    try {
      await api.delete(`/stockage/fichiers/${f.id}`);
      setFichiers((prev) => prev.filter((x) => x.id !== f.id));
      await rechargerProfil();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  const usageMo = profil ? profil.stockage.usage_octets / (1024 * 1024) : 0;
  const quotaMo = profil?.stockage.quota_mo ?? 0;
  const pct = quotaMo > 0 ? Math.min(100, Math.round((usageMo / quotaMo) * 100)) : 0;

  return (
    <>
      <div className="section-titre">
        <FolderOpen size={17} /> Mes fichiers
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5 }}>
          <span className="muted">Espace utilisé</span>
          <strong>
            {usageMo.toFixed(1)} Mo / {quotaMo.toFixed(0)} Mo
          </strong>
        </div>
        <div className={`progress ${pct > 85 ? "danger" : ""}`}>
          <div style={{ width: `${pct}%` }} />
        </div>
        <input
          ref={inputRef}
          type="file"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />
        <button className="btn btn-primary" onClick={() => inputRef.current?.click()} disabled={uploading}>
          <Upload size={15} /> {uploading ? "Envoi en cours..." : "Envoyer un fichier"}
        </button>
      </div>

      {error && <p className="error fade-in">{error}</p>}

      <div className="card">
        {fichiers.length === 0 ? (
          <div className="empty-state">
            Aucun fichier. Envoyez vos documents ici pour les retrouver à chaque visite — ou pour les faire imprimer.
          </div>
        ) : (
          <div className="liste">
            {fichiers.map((f) => (
              <div className="liste-item" key={f.id}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {f.nom_original}
                  </div>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {formatTaille(f.taille_octets)} · {new Date(f.date_upload).toLocaleDateString()}
                  </span>
                </div>
                <button
                  className="icon-btn"
                  title="Télécharger"
                  onClick={() => downloadFile(`/stockage/fichiers/${f.id}/download`, f.nom_original)}
                >
                  <Download size={17} />
                </button>
                <button className="icon-btn" title="Supprimer" onClick={() => handleDelete(f)}>
                  <Trash2 size={17} style={{ color: "var(--danger)" }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
