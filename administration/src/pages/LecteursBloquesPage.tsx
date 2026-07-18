import { useCallback, useEffect, useState } from "react";
import { HardDriveDownload } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
import type { LecteurBloque, PlateformeLecteur, Poste, TypeLecteur } from "../api/types";

function typeLabel(type: TypeLecteur): string {
  if (type === "amovible") return "Clé USB / disque amovible";
  if (type === "cd_dvd") return "Lecteur CD/DVD";
  if (type === "reseau") return "Lecteur réseau";
  return type;
}

function plateformeLabel(plateforme: PlateformeLecteur): string {
  if (plateforme === "windows") return "Windows";
  if (plateforme === "linux") return "Linux";
  return "Toutes plateformes";
}

export default function LecteursBloquesPage() {
  const { isAdmin } = usePermissions();
  const [regles, setRegles] = useState<LecteurBloque[]>([]);
  const [postes, setPostes] = useState<Poste[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reglesData, postesData] = await Promise.all([
        api.get<LecteurBloque[]>("/lecteur-bloque/"),
        api.get<Poste[]>("/poste/"),
      ]);
      setRegles(reglesData);
      setPostes(postesData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function posteLabel(regle: LecteurBloque): string {
    if (regle.poste_id == null) return "Tous les postes";
    const poste = postes.find((p) => p.id === regle.poste_id);
    return poste?.nom ?? `#${regle.poste_id}`;
  }

  async function toggleActif(regle: LecteurBloque) {
    try {
      const updated = await api.patch<LecteurBloque>(`/lecteur-bloque/${regle.id}`, { actif: !regle.actif });
      setRegles((prev) => prev.map((r) => (r.id === regle.id ? updated : r)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDelete(regle: LecteurBloque) {
    if (!confirm(`Supprimer la règle de blocage « ${typeLabel(regle.type_lecteur)} » (${posteLabel(regle)}) ?`)) return;
    try {
      await api.delete(`/lecteur-bloque/${regle.id}`);
      setRegles((prev) => prev.filter((r) => r.id !== regle.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <HardDriveDownload size={20} /> Lecteurs bloqués
        </h1>
        {isAdmin && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + Nouvelle règle
          </button>
        )}
      </div>

      <p className="muted">
        Bloque en continu les types de lecteurs choisis (clé USB, CD/DVD, lecteur réseau) sur les
        postes clients. Une règle globale (sans poste spécifique) s'applique à tous les postes ;
        le lecteur système n'est jamais concerné.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : regles.length === 0 ? (
          <div className="empty-state">Aucune règle de blocage</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Type de lecteur</th>
                <th>Plateforme</th>
                <th>S'applique à</th>
                <th>Description</th>
                <th>Statut</th>
                {isAdmin && <th></th>}
              </tr>
            </thead>
            <tbody>
              {regles.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{typeLabel(r.type_lecteur)}</strong>
                  </td>
                  <td className="muted">{plateformeLabel(r.plateforme)}</td>
                  <td className="muted">{posteLabel(r)}</td>
                  <td className="muted">{r.description || "—"}</td>
                  <td>
                    <span className={`badge ${r.actif ? "badge-success" : "badge-neutral"}`}>
                      {r.actif ? "Active" : "Inactive"}
                    </span>
                  </td>
                  {isAdmin && (
                    <td>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn-sm" onClick={() => toggleActif(r)}>
                          {r.actif ? "Désactiver" : "Activer"}
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(r)}>
                          Supprimer
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
        <CreateLecteurBloqueModal
          postes={postes}
          onClose={() => setShowCreate(false)}
          onCreated={(regle) => {
            setRegles((prev) => [regle, ...prev]);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}

function CreateLecteurBloqueModal({
  postes,
  onClose,
  onCreated,
}: {
  postes: Poste[];
  onClose: () => void;
  onCreated: (regle: LecteurBloque) => void;
}) {
  const [typeLecteur, setTypeLecteur] = useState<TypeLecteur>("amovible");
  const [plateforme, setPlateforme] = useState<PlateformeLecteur>("tous");
  const [posteId, setPosteId] = useState("tous");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        type_lecteur: typeLecteur,
        plateforme,
        description: description.trim() || null,
      };
      if (posteId !== "tous") payload.poste_id = parseInt(posteId, 10);

      const regle = await api.post<LecteurBloque>("/lecteur-bloque/", payload);
      onCreated(regle);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouvelle règle de blocage</h2>
        {error && <p className="error">{error}</p>}

        <label>
          Type de lecteur
          <select value={typeLecteur} onChange={(e) => setTypeLecteur(e.target.value as TypeLecteur)}>
            <option value="amovible">Clé USB / disque amovible</option>
            <option value="cd_dvd">Lecteur CD/DVD</option>
            <option value="reseau">Lecteur réseau</option>
          </select>
        </label>

        <label>
          Plateforme
          <select value={plateforme} onChange={(e) => setPlateforme(e.target.value as PlateformeLecteur)}>
            <option value="tous">Toutes plateformes</option>
            <option value="windows">Windows</option>
            <option value="linux">Linux</option>
          </select>
        </label>

        <label>
          S'applique à
          <select value={posteId} onChange={(e) => setPosteId(e.target.value)}>
            <option value="tous">Tous les postes</option>
            {postes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nom}
              </option>
            ))}
          </select>
        </label>

        <label>
          Description (optionnel)
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="ex: Blocage clés USB accueil" />
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
