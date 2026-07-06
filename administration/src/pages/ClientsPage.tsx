import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { ClientUser, TypePaiement } from "../api/types";

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [rechargeTarget, setRechargeTarget] = useState<ClientUser | null>(null);

  const load = useCallback(async (searchTerm: string) => {
    setLoading(true);
    setError(null);
    try {
      const path = searchTerm.trim()
        ? `/user/query/clients?username=${encodeURIComponent(searchTerm.trim())}`
        : "/user/clients";
      const data = await api.get<ClientUser[]>(path);
      setClients(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load("");
  }, [load]);

  function handleSearchSubmit(e: FormEvent) {
    e.preventDefault();
    load(search);
  }

  async function toggleActive(client: ClientUser) {
    try {
      await api.patch(`/user/setupdateUser/${client.username}?active=${!client.is_active}`);
      setClients((prev) =>
        prev.map((c) => (c.username === client.username ? { ...c, is_active: !c.is_active } : c))
      );
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Clients</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nouveau client
        </button>
      </div>

      <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8 }}>
        <input
          placeholder="Rechercher par nom d'utilisateur..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 320 }}
        />
        <button type="submit" className="btn">
          Rechercher
        </button>
        {search && (
          <button
            type="button"
            className="btn"
            onClick={() => {
              setSearch("");
              load("");
            }}
          >
            Réinitialiser
          </button>
        )}
      </form>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : clients.length === 0 ? (
          <div className="empty-state">Aucun client trouvé</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Solde</th>
                <th>Abonnement</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.id}>
                  <td>
                    <strong>{c.username}</strong>
                    <div className="muted">{c.email}</div>
                  </td>
                  <td>{c.solde_euros.toFixed(2)}€</td>
                  <td>
                    {c.abonnement_courant ? (
                      <span className={`badge ${c.abonnement_courant.est_suspendu ? "badge-warning" : "badge-success"}`}>
                        {c.abonnement_courant.illimite
                          ? "Illimité"
                          : c.abonnement_courant.minutes_restantes_aujourdhui != null
                            ? `${c.abonnement_courant.minutes_restantes_aujourdhui} min restantes`
                            : "Actif"}
                      </span>
                    ) : (
                      <span className="muted">Aucun</span>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${c.is_active ? "badge-success" : "badge-neutral"}`}>
                      {c.is_active ? "Actif" : "Inactif"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <button className="btn btn-sm" onClick={() => setRechargeTarget(c)}>
                        Recharger
                      </button>
                      <button className="btn btn-sm" onClick={() => toggleActive(c)}>
                        {c.is_active ? "Désactiver" : "Activer"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateClientModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load(search);
          }}
        />
      )}

      {rechargeTarget && (
        <RechargeModal
          client={rechargeTarget}
          onClose={() => setRechargeTarget(null)}
          onDone={(nouveauSolde) => {
            setClients((prev) =>
              prev.map((c) => (c.id === rechargeTarget.id ? { ...c, solde_euros: nouveauSolde } : c))
            );
            setRechargeTarget(null);
          }}
        />
      )}
    </div>
  );
}

function CreateClientModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/user/createClient", {
        username,
        email,
        password,
        first_name: firstName,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouveau client</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom d'utilisateur
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
        </label>
        <label>
          Prénom
          <input value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Mot de passe
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
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

function RechargeModal({
  client,
  onClose,
  onDone,
}: {
  client: ClientUser;
  onClose: () => void;
  onDone: (nouveauSolde: number) => void;
}) {
  const [montant, setMontant] = useState("5");
  const [typePaiement, setTypePaiement] = useState<TypePaiement>("especes");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const result = await api.post<{ solde_euros: number }>(
        `/paiement/recharge/${client.username}?montant=${encodeURIComponent(montant)}&type_paiement=${typePaiement}`
      );
      onDone(result.solde_euros);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la recharge");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Recharger le solde — {client.username}</h2>
        <p className="muted">Solde actuel : {client.solde_euros.toFixed(2)}€</p>
        {error && <p className="error">{error}</p>}
        <label>
          Montant (€)
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={montant}
            onChange={(e) => setMontant(e.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          Moyen de paiement
          <select value={typePaiement} onChange={(e) => setTypePaiement(e.target.value as TypePaiement)}>
            <option value="especes">Espèces</option>
            <option value="carte">Carte</option>
            <option value="mobile_money">Mobile money</option>
            <option value="virement">Virement</option>
          </select>
        </label>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Enregistrement..." : "Recharger"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
