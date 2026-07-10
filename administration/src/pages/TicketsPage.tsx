import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Ticket as TicketIcon, Plus, Printer, PlusCircle } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
import { BulkBar, executerActionGroupee, resumeActionGroupee, useSelection } from "../components/BulkBar";
import type { Offre, TicketEntry } from "../api/types";
import { printTicketsBatch } from "../utils/receipt";

const STATUT_LABEL = (t: TicketEntry) => {
  if (t.est_consomme) return { label: "Utilisé", cls: "badge-neutral" };
  if (!t.est_actif) return { label: "Désactivé", cls: "badge-danger" };
  return { label: "Disponible", cls: "badge-success" };
};

export default function TicketsPage() {
  const { hasPermission } = usePermissions();
  const peutVendre = hasPermission("catalogue");
  const { selected, toggle, toggleAll, clear } = useSelection<string>();
  const [tickets, setTickets] = useState<TicketEntry[]>([]);
  const [offres, setOffres] = useState<Offre[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statutFilter, setStatutFilter] = useState<"" | "actif" | "inactif" | "consomme" | "disponible">("");
  const [showGenerate, setShowGenerate] = useState(false);
  const [renforcerTarget, setRenforcerTarget] = useState<TicketEntry | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [t, o] = await Promise.all([
        api.get<TicketEntry[]>("/tickets/"),
        api.get<Offre[]>("/offre/"),
      ]);
      setTickets(t);
      setOffres(o);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleToggleActif(t: TicketEntry) {
    try {
      const updated = await api.patch<TicketEntry>(`/tickets/${t.code}/${t.est_actif ? "desactiver" : "reactiver"}`);
      setTickets((prev) => prev.map((x) => (x.code === t.code ? updated : x)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  function handleReprint(t: TicketEntry) {
    printTicketsBatch([{ code: t.code, forfait: t.offre_nom || "Ticket", prix: t.offre_prix ?? undefined }]);
  }

  const visibleTickets = tickets.filter((t) => {
    if (statutFilter === "actif") return t.est_actif;
    if (statutFilter === "inactif") return !t.est_actif;
    if (statutFilter === "consomme") return t.est_consomme;
    if (statutFilter === "disponible") return t.est_actif && !t.est_consomme;
    return true;
  });

  const ticketsSelectionnes = visibleTickets.filter((t) => selected.has(t.code));

  async function bulkActif(actif: boolean) {
    const cibles = ticketsSelectionnes.filter((t) => t.est_actif !== actif);
    const resultat = await executerActionGroupee(cibles, (t) =>
      api.patch(`/tickets/${t.code}/${actif ? "reactiver" : "desactiver"}`)
    );
    alert(resumeActionGroupee(actif ? "Réactivation" : "Désactivation", resultat));
    clear();
    load();
  }

  function bulkReimprimer() {
    printTicketsBatch(
      ticketsSelectionnes.map((t) => ({ code: t.code, forfait: t.offre_nom || "Ticket", prix: t.offre_prix ?? undefined }))
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <TicketIcon size={20} /> Tickets
        </h1>
        {peutVendre && (
          <button className="btn btn-primary" onClick={() => setShowGenerate(true)}>
            <Plus size={15} /> Générer des tickets
          </button>
        )}
      </div>
      <p className="page-subtitle">
        Tous les tickets émis, leur statut d'utilisation, et les actions de suivi (désactiver, renforcer...).
      </p>

      <div className="card" style={{ display: "flex", gap: 8 }}>
        <select value={statutFilter} onChange={(e) => setStatutFilter(e.target.value as typeof statutFilter)}>
          <option value="">Tous les statuts</option>
          <option value="disponible">Disponibles</option>
          <option value="consomme">Utilisés</option>
          <option value="inactif">Désactivés</option>
          <option value="actif">Actifs</option>
        </select>
      </div>

      {error && <p className="error">{error}</p>}

      <BulkBar count={ticketsSelectionnes.length} onClear={clear}>
        <button className="btn btn-sm" onClick={bulkReimprimer}>
          <Printer size={13} /> Réimprimer la sélection
        </button>
        {peutVendre && (
          <>
            <button className="btn btn-sm" onClick={() => bulkActif(false)}>
              Désactiver la sélection
            </button>
            <button className="btn btn-sm" onClick={() => bulkActif(true)}>
              Réactiver la sélection
            </button>
          </>
        )}
      </BulkBar>

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : visibleTickets.length === 0 ? (
          <div className="empty-state">Aucun ticket</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{ width: 28 }}>
                  <input
                    type="checkbox"
                    checked={visibleTickets.length > 0 && visibleTickets.every((t) => selected.has(t.code))}
                    onChange={() => toggleAll(visibleTickets.map((t) => t.code))}
                  />
                </th>
                <th>Code</th>
                <th>Forfait</th>
                <th>Restant</th>
                <th>Statut</th>
                <th>Émis le</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visibleTickets.map((t) => {
                const statut = STATUT_LABEL(t);
                return (
                  <tr key={t.id}>
                    <td>
                      <input type="checkbox" checked={selected.has(t.code)} onChange={() => toggle(t.code)} />
                    </td>
                    <td>
                      <code>{t.code}</code>
                    </td>
                    <td className="muted">{t.offre_nom || "—"}</td>
                    <td className="muted">
                      {t.restant_minutes != null ? `${t.restant_minutes} min` : ""}
                      {t.restant_data_mo != null ? ` ${t.restant_data_mo} Mo` : ""}
                      {t.restant_minutes == null && t.restant_data_mo == null && "—"}
                    </td>
                    <td>
                      <span className={`badge ${statut.cls}`}>{statut.label}</span>
                    </td>
                    <td className="muted">{new Date(t.date_achat).toLocaleDateString()}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn-sm" onClick={() => handleReprint(t)}>
                          <Printer size={13} />
                        </button>
                        {peutVendre && !t.est_consomme && (
                          <button className="btn btn-sm" onClick={() => setRenforcerTarget(t)}>
                            <PlusCircle size={13} /> Renforcer
                          </button>
                        )}
                        {peutVendre && (
                          <button className="btn btn-sm" onClick={() => handleToggleActif(t)}>
                            {t.est_actif ? "Désactiver" : "Réactiver"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showGenerate && (
        <GenerateTicketsModal
          offres={offres}
          onClose={() => setShowGenerate(false)}
          onGenerated={() => {
            setShowGenerate(false);
            load();
          }}
        />
      )}

      {renforcerTarget && (
        <RenforcerModal
          ticket={renforcerTarget}
          onClose={() => setRenforcerTarget(null)}
          onDone={(updated) => {
            setTickets((prev) => prev.map((x) => (x.code === updated.code ? updated : x)));
            setRenforcerTarget(null);
          }}
        />
      )}
    </div>
  );
}

function GenerateTicketsModal({
  offres,
  onClose,
  onGenerated,
}: {
  offres: Offre[];
  onClose: () => void;
  onGenerated: () => void;
}) {
  const [offreId, setOffreId] = useState(offres[0]?.id ? String(offres[0].id) : "");
  const [nombre, setNombre] = useState("10");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!offreId) {
      setError("Choisissez un forfait");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const result = await api.post<{ code: string; forfait: string; prix: number }[]>(
        `/tickets/generate?forfait_id=${offreId}&nbticket=${nombre}`
      );
      printTicketsBatch(result);
      onGenerated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la génération");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Générer des tickets</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Forfait
          <select value={offreId} onChange={(e) => setOffreId(e.target.value)} required>
            <option value="">Choisir...</option>
            {offres.map((o) => (
              <option key={o.id} value={o.id}>
                {o.nom} — {o.prix.toFixed(2)}€
              </option>
            ))}
          </select>
        </label>
        <label>
          Nombre de tickets
          <input type="number" min="1" max="200" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        </label>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Génération..." : "Générer et imprimer"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}

function RenforcerModal({
  ticket,
  onClose,
  onDone,
}: {
  ticket: TicketEntry;
  onClose: () => void;
  onDone: (t: TicketEntry) => void;
}) {
  const [minutes, setMinutes] = useState("30");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const updated = await api.post<TicketEntry>(`/tickets/${ticket.code}/renforcer?minutes=${minutes}`);
      onDone(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Renforcer le ticket {ticket.code}</h2>
        <p className="muted">Temps restant actuel : {ticket.restant_minutes ?? 0} min</p>
        {error && <p className="error">{error}</p>}
        <label>
          Minutes à ajouter
          <input type="number" min="1" value={minutes} onChange={(e) => setMinutes(e.target.value)} required />
        </label>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Enregistrement..." : "Ajouter"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
