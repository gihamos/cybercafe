import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { BandePassanteProfil, TypeProfilBP } from "../api/types";

const TYPE_LABELS: Record<TypeProfilBP, string> = {
  offre: "Offre",
  abonnement: "Abonnement",
  ticket: "Ticket",
  user: "Utilisateur",
  poste: "Poste",
};

export default function BandePassantePage() {
  const [profils, setProfils] = useState<BandePassanteProfil[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<BandePassanteProfil[]>("/bande-passante/profils");
      setProfils(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function cibleLabel(p: BandePassanteProfil): string {
    if (p.offre_id) return `Offre #${p.offre_id}`;
    if (p.abonnement_id) return `Abonnement #${p.abonnement_id}`;
    if (p.ticket_id) return `Ticket #${p.ticket_id}`;
    if (p.user_id) return `Utilisateur #${p.user_id}`;
    if (p.poste_id) return `Poste #${p.poste_id}`;
    return "—";
  }

  async function handleDelete(p: BandePassanteProfil) {
    if (!confirm("Supprimer ce profil de bande passante ?")) return;
    try {
      await api.delete(`/bande-passante/profils/${p.id}`);
      setProfils((prev) => prev.filter((x) => x.id !== p.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Bande passante</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nouveau profil
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : profils.length === 0 ? (
          <div className="empty-state">Aucun profil de bande passante</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Cible</th>
                <th>Débit (down/up)</th>
                <th>Quota (jour/mois)</th>
                <th>Blocage si dépassé</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {profils.map((p) => (
                <tr key={p.id}>
                  <td>{TYPE_LABELS[p.type_profil]}</td>
                  <td className="muted">{cibleLabel(p)}</td>
                  <td className="muted">
                    {p.download_mbps ?? "—"} / {p.upload_mbps ?? "—"} Mbps
                  </td>
                  <td className="muted">
                    {p.quota_journalier_mo ?? "—"} / {p.quota_mensuel_mo ?? "—"} Mo
                  </td>
                  <td>
                    <span className={`badge ${p.bloquer_si_depasse ? "badge-warning" : "badge-neutral"}`}>
                      {p.bloquer_si_depasse ? "Oui" : "Non"}
                    </span>
                  </td>
                  <td>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p)}>
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateProfilModal
          onClose={() => setShowCreate(false)}
          onCreated={(profil) => {
            setProfils((prev) => [profil, ...prev]);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}

function CreateProfilModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (profil: BandePassanteProfil) => void;
}) {
  const [typeProfil, setTypeProfil] = useState<TypeProfilBP>("user");
  const [cibleId, setCibleId] = useState("");
  const [downloadMbps, setDownloadMbps] = useState("");
  const [uploadMbps, setUploadMbps] = useState("");
  const [quotaJournalier, setQuotaJournalier] = useState("");
  const [quotaMensuel, setQuotaMensuel] = useState("");
  const [bloquerSiDepasse, setBloquerSiDepasse] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        type_profil: typeProfil,
        download_mbps: downloadMbps ? parseFloat(downloadMbps) : null,
        upload_mbps: uploadMbps ? parseFloat(uploadMbps) : null,
        quota_journalier_mo: quotaJournalier ? parseFloat(quotaJournalier) : null,
        quota_mensuel_mo: quotaMensuel ? parseFloat(quotaMensuel) : null,
        bloquer_si_depasse: bloquerSiDepasse,
      };
      if (cibleId) payload[`${typeProfil}_id`] = parseInt(cibleId, 10);

      const profil = await api.post<BandePassanteProfil>("/bande-passante/profils", payload);
      onCreated(profil);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouveau profil de bande passante</h2>
        {error && <p className="error">{error}</p>}

        <label>
          Type de cible
          <select value={typeProfil} onChange={(e) => setTypeProfil(e.target.value as TypeProfilBP)}>
            <option value="user">Utilisateur</option>
            <option value="poste">Poste</option>
            <option value="ticket">Ticket</option>
            <option value="offre">Offre</option>
            <option value="abonnement">Abonnement</option>
          </select>
        </label>
        <label>
          ID de la cible ({TYPE_LABELS[typeProfil]})
          <input type="number" value={cibleId} onChange={(e) => setCibleId(e.target.value)} required />
        </label>

        <div className="form-grid">
          <label>
            Débit descendant (Mbps)
            <input type="number" step="0.1" min="0" value={downloadMbps} onChange={(e) => setDownloadMbps(e.target.value)} />
          </label>
          <label>
            Débit montant (Mbps)
            <input type="number" step="0.1" min="0" value={uploadMbps} onChange={(e) => setUploadMbps(e.target.value)} />
          </label>
          <label>
            Quota journalier (Mo)
            <input type="number" step="1" min="0" value={quotaJournalier} onChange={(e) => setQuotaJournalier(e.target.value)} />
          </label>
          <label>
            Quota mensuel (Mo)
            <input type="number" step="1" min="0" value={quotaMensuel} onChange={(e) => setQuotaMensuel(e.target.value)} />
          </label>
        </div>

        <label>
          <input
            type="checkbox"
            checked={bloquerSiDepasse}
            onChange={(e) => setBloquerSiDepasse(e.target.checked)}
            style={{ width: "auto", marginRight: 6 }}
          />
          Bloquer automatiquement si le quota est dépassé
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
