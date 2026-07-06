import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Paiement, StatutPaiement, TypePaiement } from "../api/types";

const STATUT_BADGE: Record<StatutPaiement, string> = {
  succes: "badge-success",
  echec: "badge-danger",
  annule: "badge-neutral",
  en_attente: "badge-warning",
};

export default function PaiementsPage() {
  const [paiements, setPaiements] = useState<Paiement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statutFilter, setStatutFilter] = useState<StatutPaiement | "">("");
  const [typeFilter, setTypeFilter] = useState<TypePaiement | "">("");

  const load = useCallback(async (statut: string, type: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (statut) params.set("statut", statut);
      if (type) params.set("type_paiement", type);
      const data = await api.get<Paiement[]>(`/paiement/?${params}`);
      setPaiements(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(statutFilter, typeFilter);
  }, [load, statutFilter, typeFilter]);

  async function handleRembourser(paiement: Paiement) {
    if (!confirm(`Rembourser le paiement de ${paiement.montant.toFixed(2)}€ ?`)) return;
    try {
      const updated = await api.post<Paiement>(`/paiement/${paiement.id}/rembourser`);
      setPaiements((prev) => prev.map((p) => (p.id === paiement.id ? updated : p)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Paiements</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={statutFilter} onChange={(e) => setStatutFilter(e.target.value as StatutPaiement | "")}>
            <option value="">Tous les statuts</option>
            <option value="succes">Succès</option>
            <option value="en_attente">En attente</option>
            <option value="echec">Échec</option>
            <option value="annule">Annulé</option>
          </select>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as TypePaiement | "")}>
            <option value="">Tous les moyens</option>
            <option value="especes">Espèces</option>
            <option value="carte">Carte</option>
            <option value="mobile_money">Mobile money</option>
            <option value="virement">Virement</option>
            <option value="paypal">PayPal</option>
          </select>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : paiements.length === 0 ? (
          <div className="empty-state">Aucun paiement</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Client</th>
                <th>Montant</th>
                <th>Moyen</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {paiements.map((p) => (
                <tr key={p.id}>
                  <td className="muted">{new Date(p.date_paiement).toLocaleString()}</td>
                  <td>{p.user_id ? `#${p.user_id}` : p.ticket_id ? `Ticket #${p.ticket_id}` : "—"}</td>
                  <td>{p.montant.toFixed(2)}€</td>
                  <td className="muted">{p.type_paiement}</td>
                  <td>
                    <span className={`badge ${STATUT_BADGE[p.statut]}`}>{p.statut}</span>
                  </td>
                  <td>
                    {p.statut === "succes" && (
                      <button className="btn btn-sm btn-danger" onClick={() => handleRembourser(p)}>
                        Rembourser
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
