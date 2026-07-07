import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { PayConnectRequestEntry, Poste } from "../api/types";
import { useAdminSocket } from "../ws/useAdminSocket";

export default function PayConnectPage() {
  const [demandes, setDemandes] = useState<PayConnectRequestEntry[]>([]);
  const [postes, setPostes] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    api.get<Poste[]>("/poste/").then((list) => {
      setPostes(Object.fromEntries(list.map((p) => [p.id, p.nom])));
    }).catch(() => {});
    refresh();
  }, []);

  async function refresh() {
    try {
      const data = await api.get<PayConnectRequestEntry[]>("/pay-connect/en-attente");
      setDemandes(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    }
  }

  useAdminSocket(
    useCallback((msg) => {
      if (msg.type === "pay_connect_pending") {
        setDemandes((prev) => (prev.some((d) => d.id === msg.data.id) ? prev : [...prev, { ...msg.data, statut: "en_attente", operateur_id: null, date_creation: new Date().toISOString(), date_traitement: null }]));
      } else if (msg.type === "pay_connect_cancelled") {
        setDemandes((prev) => prev.filter((d) => d.id !== msg.data.id));
      }
    }, [])
  );

  async function handleConfirmer(id: number) {
    setBusyId(id);
    try {
      await api.post(`/pay-connect/${id}/confirmer`);
      setDemandes((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Échec de la confirmation");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRefuser(id: number) {
    setBusyId(id);
    try {
      await api.post(`/pay-connect/${id}/refuser`);
      setDemandes((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Échec du refus");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <h1>Pay &amp; Connect</h1>
      <p className="muted">
        Demandes de connexion rapide payées en espèces au comptoir — encaissez puis confirmez pour démarrer la
        session sur le poste, ou refusez.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {demandes.length === 0 ? (
          <div className="empty-state">Aucune demande en attente</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Poste</th>
                <th>Durée</th>
                <th>Montant</th>
                <th>Demandé à</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {demandes.map((d) => (
                <tr key={d.id}>
                  <td>{postes[d.poste_id] || `Poste #${d.poste_id}`}</td>
                  <td>{d.minutes} min</td>
                  <td>{d.montant.toFixed(2)}€</td>
                  <td className="muted">{new Date(d.date_creation).toLocaleTimeString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <button className="btn btn-sm btn-primary" disabled={busyId === d.id} onClick={() => handleConfirmer(d.id)}>
                        Confirmer (espèces reçues)
                      </button>
                      <button className="btn btn-sm btn-danger" disabled={busyId === d.id} onClick={() => handleRefuser(d.id)}>
                        Refuser
                      </button>
                    </div>
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
