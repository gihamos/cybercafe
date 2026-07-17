import { useCallback, useEffect, useState } from "react";
import { Package } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
import { BulkBar, executerActionGroupee, resumeActionGroupee, useSelection } from "../components/BulkBar";
import type { Offre, TypeOffre, UniteDuree } from "../api/types";

const TYPE_LABELS: Record<TypeOffre, string> = {
  temps: "Temps",
  data: "Data",
  illimite: "Illimité",
};

export default function OffresPage() {
  const { hasPermission } = usePermissions();
  const peutGerer = hasPermission("creation_forfaits");
  const { selected, toggle, toggleAll, clear } = useSelection<number>();
  const [offres, setOffres] = useState<Offre[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Offre[]>("/offre/");
      setOffres(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleActif(offre: Offre) {
    try {
      const updated = await api.patch<Offre>(`/offre/${offre.id}/actif?actif=${!offre.is_actif}`);
      setOffres((prev) => prev.map((o) => (o.id === offre.id ? updated : o)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDelete(offre: Offre) {
    if (!confirm(`Supprimer l'offre « ${offre.nom} » ?`)) return;
    try {
      await api.delete(`/offre/${offre.id}`);
      setOffres((prev) => prev.filter((o) => o.id !== offre.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  const offresSelectionnees = offres.filter((o) => selected.has(o.id));

  async function bulkActif(actif: boolean) {
    const cibles = offresSelectionnees.filter((o) => o.is_actif !== actif);
    const resultat = await executerActionGroupee(cibles, (o) => api.patch(`/offre/${o.id}/actif?actif=${actif}`));
    alert(resumeActionGroupee(actif ? "Activation" : "Désactivation", resultat));
    clear();
    load();
  }

  async function bulkSupprimer() {
    if (!confirm(`Supprimer ${offresSelectionnees.length} offre(s) ?`)) return;
    const resultat = await executerActionGroupee(offresSelectionnees, (o) => api.delete(`/offre/${o.id}`));
    alert(resumeActionGroupee("Suppression", resultat));
    clear();
    load();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Package size={20} /> Offres / Forfaits
        </h1>
        {peutGerer && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + Nouvelle offre
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {peutGerer && (
        <BulkBar count={offresSelectionnees.length} onClear={clear}>
          <button className="btn btn-sm" onClick={() => bulkActif(true)}>
            Activer la sélection
          </button>
          <button className="btn btn-sm" onClick={() => bulkActif(false)}>
            Désactiver la sélection
          </button>
          <button className="btn btn-sm btn-danger" onClick={bulkSupprimer}>
            Supprimer la sélection
          </button>
        </BulkBar>
      )}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : offres.length === 0 ? (
          <div className="empty-state">Aucune offre</div>
        ) : (
          <table>
            <thead>
              <tr>
                {peutGerer && (
                  <th style={{ width: 28 }}>
                    <input
                      type="checkbox"
                      checked={offres.length > 0 && offres.every((o) => selected.has(o.id))}
                      onChange={() => toggleAll(offres.map((o) => o.id))}
                    />
                  </th>
                )}
                <th>Nom</th>
                <th>Type</th>
                <th>Détail</th>
                <th>Prix</th>
                <th>Statut</th>
                {peutGerer && <th></th>}
              </tr>
            </thead>
            <tbody>
              {offres.map((o) => (
                <tr key={o.id}>
                  {peutGerer && (
                    <td>
                      <input type="checkbox" checked={selected.has(o.id)} onChange={() => toggle(o.id)} />
                    </td>
                  )}
                  <td>
                    <strong>{o.nom}</strong>
                    {o.description && <div className="muted">{o.description}</div>}
                  </td>
                  <td>{TYPE_LABELS[o.type_offre]}</td>
                  <td className="muted">
                    {o.type_offre === "temps" && o.duree_minutes != null && `${o.duree_minutes} min`}
                    {o.type_offre === "data" && o.quota_mo != null && `${o.quota_mo} Mo`}
                    {o.type_offre === "illimite" && "—"}
                    {o.unite_duree && ` / ${o.valeur_duree} ${o.unite_duree}`}
                    {" · "}{o.max_sessions_simultanees || 1} session{(o.max_sessions_simultanees || 1) > 1 ? "s" : ""} max
                  </td>
                  <td>{o.prix.toFixed(2)}€</td>
                  <td>
                    <span className={`badge ${o.is_actif ? "badge-success" : "badge-neutral"}`}>
                      {o.is_actif ? "Active" : "Inactive"}
                    </span>
                  </td>
                  {peutGerer && (
                    <td>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn-sm" onClick={() => toggleActif(o)}>
                          {o.is_actif ? "Désactiver" : "Activer"}
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(o)}>
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
        <CreateOffreModal
          onClose={() => setShowCreate(false)}
          onCreated={(offre) => {
            setOffres((prev) => [...prev, offre]);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}

function CreateOffreModal({ onClose, onCreated }: { onClose: () => void; onCreated: (offre: Offre) => void }) {
  const [nom, setNom] = useState("");
  const [typeOffre, setTypeOffre] = useState<TypeOffre>("temps");
  const [prix, setPrix] = useState("2.00");
  const [dureeMinutes, setDureeMinutes] = useState("60");
  const [quotaMo, setQuotaMo] = useState("500");
  const [uniteDuree, setUniteDuree] = useState<UniteDuree | "">("jour");
  const [valeurDuree, setValeurDuree] = useState("1");
  const [maxSessions, setMaxSessions] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        nom,
        type_offre: typeOffre,
        prix: parseFloat(prix),
        unite_duree: uniteDuree || null,
        valeur_duree: uniteDuree ? parseInt(valeurDuree, 10) : null,
        max_sessions_simultanees: maxSessions ? parseInt(maxSessions, 10) : null,
      };
      if (typeOffre === "temps") payload.duree_minutes = parseInt(dureeMinutes, 10);
      if (typeOffre === "data") payload.quota_mo = parseFloat(quotaMo);

      const offre = await api.post<Offre>("/offre/", payload);
      onCreated(offre);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouvelle offre</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom
          <input value={nom} onChange={(e) => setNom(e.target.value)} required autoFocus />
        </label>
        <label>
          Type
          <select value={typeOffre} onChange={(e) => setTypeOffre(e.target.value as TypeOffre)}>
            <option value="temps">Temps</option>
            <option value="data">Data</option>
            <option value="illimite">Illimité</option>
          </select>
        </label>
        {typeOffre === "temps" && (
          <label>
            Durée (minutes)
            <input type="number" min="1" value={dureeMinutes} onChange={(e) => setDureeMinutes(e.target.value)} required />
          </label>
        )}
        {typeOffre === "data" && (
          <label>
            Quota (Mo)
            <input type="number" min="1" value={quotaMo} onChange={(e) => setQuotaMo(e.target.value)} required />
          </label>
        )}
        <label>
          Prix (€)
          <input type="number" step="0.01" min="0" value={prix} onChange={(e) => setPrix(e.target.value)} required />
        </label>
        <div className="form-grid">
          <label>
            Durée de validité
            <select value={uniteDuree} onChange={(e) => setUniteDuree(e.target.value as UniteDuree | "")}>
              <option value="">Aucune</option>
              <option value="minute">Minute(s)</option>
              <option value="heure">Heure(s)</option>
              <option value="jour">Jour(s)</option>
              <option value="hebdo">Semaine(s)</option>
              <option value="mois">Mois</option>
              <option value="annee">Année(s)</option>
            </select>
          </label>
          {uniteDuree && (
            <label>
              Valeur
              <input type="number" min="1" value={valeurDuree} onChange={(e) => setValeurDuree(e.target.value)} />
            </label>
          )}
        </div>
        <label>
          Sessions actives simultanées max
          <input
            type="number" min="1" placeholder="1 (par défaut)"
            value={maxSessions} onChange={(e) => setMaxSessions(e.target.value)}
          />
        </label>
        <p className="muted" style={{ fontSize: 12.5, marginTop: -8 }}>
          Nombre d'appareils pouvant se connecter en même temps avec un ticket/abonnement de cette offre. Laisser vide pour 1 (comportement par défaut).
        </p>
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
