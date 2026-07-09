import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Ticket as TicketIcon, Plus, Printer, PlusCircle } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { Offre, TicketEntry } from "../api/types";

const STATUT_LABEL = (t: TicketEntry) => {
  if (t.est_consomme) return { label: "Utilisé", cls: "badge-neutral" };
  if (!t.est_actif) return { label: "Désactivé", cls: "badge-danger" };
  return { label: "Disponible", cls: "badge-success" };
};

function printTicketsBatch(tickets: { code: string; forfait: string }[], nomCybercafe: string) {
  const win = window.open("", "_blank", "width=500,height=700");
  if (!win) return;
  const coupons = tickets
    .map(
      (t) => `<div class="coupon">
        <div class="coupon-title">${nomCybercafe}</div>
        <div class="coupon-forfait">${t.forfait}</div>
        <div class="coupon-code">${t.code}</div>
      </div>`
    )
    .join("");
  win.document.write(`<!doctype html><html><head><title>Tickets</title><meta charset="utf-8" />
    <style>
      body { font-family: "Courier New", monospace; margin: 0; padding: 16px; }
      .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
      .coupon { border: 1px dashed #333; border-radius: 8px; padding: 14px; text-align: center; }
      .coupon-title { font-weight: bold; font-size: 13px; }
      .coupon-forfait { font-size: 12px; color: #555; margin: 4px 0; }
      .coupon-code { font-size: 18px; font-weight: bold; letter-spacing: 0.08em; margin-top: 8px; }
      @media print { .coupon { break-inside: avoid; } }
    </style>
    </head><body><div class="grid">${coupons}</div></body></html>`);
  win.document.close();
  win.focus();
  win.print();
}

export default function TicketsPage() {
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
    printTicketsBatch([{ code: t.code, forfait: t.offre_nom || "Ticket" }], "Cybercafé");
  }

  const visibleTickets = tickets.filter((t) => {
    if (statutFilter === "actif") return t.est_actif;
    if (statutFilter === "inactif") return !t.est_actif;
    if (statutFilter === "consomme") return t.est_consomme;
    if (statutFilter === "disponible") return t.est_actif && !t.est_consomme;
    return true;
  });

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <TicketIcon size={20} /> Tickets
        </h1>
        <button className="btn btn-primary" onClick={() => setShowGenerate(true)}>
          <Plus size={15} /> Générer des tickets
        </button>
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

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : visibleTickets.length === 0 ? (
          <div className="empty-state">Aucun ticket</div>
        ) : (
          <table>
            <thead>
              <tr>
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
                        {!t.est_consomme && (
                          <button className="btn btn-sm" onClick={() => setRenforcerTarget(t)}>
                            <PlusCircle size={13} /> Renforcer
                          </button>
                        )}
                        <button className="btn btn-sm" onClick={() => handleToggleActif(t)}>
                          {t.est_actif ? "Désactiver" : "Réactiver"}
                        </button>
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
      const result = await api.post<{ code: string; forfait: string }[]>(
        `/tickets/generate?forfait_id=${offreId}&nbticket=${nombre}`
      );
      printTicketsBatch(result, "Cybercafé");
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
