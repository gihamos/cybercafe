import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Pencil, Users, Eye, KeyRound, Camera, FileText } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
import { AuthenticatedImage } from "../components/AuthenticatedImage";
import { BulkBar, executerActionGroupee, resumeActionGroupee, useSelection } from "../components/BulkBar";
import type { ClientUser, TypePaiement, UserGroupEntry } from "../api/types";
import { TYPES_PIECE_IDENTITE } from "../api/types";
import { printReceipt } from "../utils/receipt";
import ClientDetailModal from "./ClientDetailModal";

export default function ClientsPage() {
  const { isAdmin } = usePermissions();
  const { selected, toggle, toggleAll, clear } = useSelection<number>();
  const [clients, setClients] = useState<ClientUser[]>([]);
  const [groups, setGroups] = useState<UserGroupEntry[]>([]);
  const [groupFilter, setGroupFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [rechargeTarget, setRechargeTarget] = useState<ClientUser | null>(null);
  const [editTarget, setEditTarget] = useState<ClientUser | null>(null);
  const [detailTarget, setDetailTarget] = useState<ClientUser | null>(null);

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
    api.get<UserGroupEntry[]>("/user-group/").then(setGroups).catch(() => {});
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

  const visibleClients = groupFilter
    ? clients.filter((c) => (c.groupe_ids || []).includes(Number(groupFilter)))
    : clients;

  const clientsSelectionnes = visibleClients.filter((c) => selected.has(c.id));

  async function bulkActive(active: boolean) {
    const cibles = clientsSelectionnes.filter((c) => c.is_active !== active);
    const resultat = await executerActionGroupee(cibles, (c) =>
      api.patch(`/user/setupdateUser/${c.username}?active=${active}`)
    );
    alert(resumeActionGroupee(active ? "Activation" : "Désactivation", resultat));
    clear();
    load(search);
  }

  async function bulkSupprimer() {
    if (!confirm(`Supprimer définitivement ${clientsSelectionnes.length} client(s) ? Cette action est irréversible.`)) return;
    const resultat = await executerActionGroupee(clientsSelectionnes, (c) => api.delete(`/user/${c.username}`));
    alert(resumeActionGroupee("Suppression", resultat));
    clear();
    load(search);
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Users size={20} /> Clients
        </h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nouveau client
        </button>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
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
        <select value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="">Tous les groupes</option>
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.nom}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}

      <BulkBar count={clientsSelectionnes.length} onClear={clear}>
        <button className="btn btn-sm" onClick={() => bulkActive(true)}>
          Activer la sélection
        </button>
        <button className="btn btn-sm" onClick={() => bulkActive(false)}>
          Désactiver la sélection
        </button>
        {isAdmin && (
          <button className="btn btn-sm btn-danger" onClick={bulkSupprimer}>
            Supprimer la sélection
          </button>
        )}
      </BulkBar>

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : visibleClients.length === 0 ? (
          <div className="empty-state">Aucun client trouvé</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{ width: 28 }}>
                  <input
                    type="checkbox"
                    checked={visibleClients.length > 0 && visibleClients.every((c) => selected.has(c.id))}
                    onChange={() => toggleAll(visibleClients.map((c) => c.id))}
                  />
                </th>
                <th>Client</th>
                <th>Groupe</th>
                <th>Solde</th>
                <th>Abonnement</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visibleClients.map((c) => (
                <tr key={c.id}>
                  <td>
                    <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} />
                  </td>
                  <td>
                    <strong>{c.username}</strong>
                    <div className="muted">{c.email}</div>
                  </td>
                  <td>
                    {c.groupe_noms && c.groupe_noms.length > 0 ? (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {c.groupe_noms.map((nom) => (
                          <span key={nom} className="badge badge-accent">
                            {nom}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="muted">—</span>
                    )}
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
                      <button className="btn btn-sm" onClick={() => setDetailTarget(c)}>
                        <Eye size={13} />
                      </button>
                      <button className="btn btn-sm" onClick={() => setEditTarget(c)}>
                        <Pencil size={13} />
                      </button>
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

      {editTarget && (
        <EditClientModal
          client={editTarget}
          groups={groups}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null);
            load(search);
          }}
        />
      )}

      {detailTarget && <ClientDetailModal client={detailTarget} onClose={() => setDetailTarget(null)} />}
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
      printReceipt({
        sousTitre: "Reçu de recharge de solde",
        lignes: [
          // Reçu anonymisé : nom/prénom plutôt que le nom d'utilisateur.
          { label: "Client", value: [client.first_name, client.last_name].filter(Boolean).join(" ") || client.username },
          { label: "Moyen", value: typePaiement },
          { label: "Nouveau solde", value: `${result.solde_euros.toFixed(2)}€` },
          { label: "Date", value: new Date().toLocaleString() },
        ],
        total: parseFloat(montant),
      });
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

function EditClientModal({
  client,
  groups,
  onClose,
  onSaved,
}: {
  client: ClientUser;
  groups: UserGroupEntry[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [address, setAddress] = useState(client.address || "");
  const [dateOfBorn, setDateOfBorn] = useState(client.date_of_born ? client.date_of_born.slice(0, 10) : "");
  const [pieceType, setPieceType] = useState(client.piece_identite_type || "");
  const [pieceNumero, setPieceNumero] = useState(client.piece_identite_numero || "");
  const [pieceOrganisme, setPieceOrganisme] = useState(client.piece_identite_organisme || "");
  const [pieceExpiration, setPieceExpiration] = useState(client.piece_identite_expiration ? client.piece_identite_expiration.slice(0, 10) : "");
  const [notes, setNotes] = useState(client.notes || "");
  const [groupeIds, setGroupeIds] = useState<number[]>(client.groupe_ids || []);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [resetResult, setResetResult] = useState<string | null>(null);
  const [hasPhoto, setHasPhoto] = useState(!!client.a_une_photo);
  const [hasPiece, setHasPiece] = useState(!!client.a_une_piece_identite);
  const [photoVersion, setPhotoVersion] = useState(0);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const pieceInputRef = useRef<HTMLInputElement>(null);

  function toggleGroupe(id: number) {
    setGroupeIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      // Particularité de l'API : PATCH /user/{username} lit ses champs dans la query
      // string, pas dans le corps JSON (comportement existant du backend).
      const params = new URLSearchParams();
      params.set("address", address);
      if (dateOfBorn) params.set("date_of_born", dateOfBorn);
      params.set("piece_identite_type", pieceType);
      params.set("piece_identite_numero", pieceNumero);
      params.set("piece_identite_organisme", pieceOrganisme);
      if (pieceExpiration) params.set("piece_identite_expiration", pieceExpiration);
      params.set("notes", notes);
      await api.patch(`/user/${client.username}?${params.toString()}`);

      // Un client peut appartenir à plusieurs groupes : on ajoute/retire uniquement
      // ce qui a changé par rapport à l'appartenance initiale.
      const original = client.groupe_ids || [];
      const toAdd = groupeIds.filter((id) => !original.includes(id));
      const toRemove = original.filter((id) => !groupeIds.includes(id));
      await Promise.all([
        ...toAdd.map((id) => api.post(`/user-group/${id}/membres/${client.id}`)),
        ...toRemove.map((id) => api.delete(`/user-group/${id}/membres/${client.id}`)),
      ]);

      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  async function handlePhotoChange(file: File) {
    setError(null);
    try {
      await api.upload(`/user/${client.username}/photo`, file);
      setHasPhoto(true);
      setPhotoVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'envoi de la photo");
    }
  }

  async function handlePieceChange(file: File) {
    setError(null);
    try {
      await api.upload(`/user/${client.username}/piece-identite/fichier`, file);
      setHasPiece(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'envoi du scan");
    }
  }

  async function handleResetPassword() {
    if (!confirm(`Générer un nouveau mot de passe provisoire pour « ${client.username} » ? L'ancien mot de passe cessera de fonctionner.`)) return;
    setError(null);
    try {
      const result = await api.post<{ mot_de_passe_provisoire: string }>(`/user/${client.username}/reset-password`);
      setResetResult(result.mot_de_passe_provisoire);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit} style={{ maxHeight: "88vh", overflowY: "auto" }}>
        <h2>Fiche client — {client.username}</h2>
        {error && <p className="error">{error}</p>}

        <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 8 }}>
          {hasPhoto ? (
            <AuthenticatedImage
              key={photoVersion}
              path={`/user/${client.username}/photo`}
              alt={client.username}
              style={{ width: 64, height: 64, borderRadius: "50%", objectFit: "cover" }}
            />
          ) : (
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "var(--surface-2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Camera size={22} className="muted" />
            </div>
          )}
          <input
            ref={photoInputRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) handlePhotoChange(file);
            }}
          />
          <button type="button" className="btn btn-sm" onClick={() => photoInputRef.current?.click()}>
            <Camera size={13} /> {hasPhoto ? "Changer la photo" : "Ajouter une photo"}
          </button>
        </div>

        <div className="form-grid">
          <label>
            Adresse
            <input value={address} onChange={(e) => setAddress(e.target.value)} />
          </label>
          <label>
            Date de naissance
            <input type="date" value={dateOfBorn} onChange={(e) => setDateOfBorn(e.target.value)} />
          </label>
        </div>

        <label>
          Groupes (un client peut en avoir plusieurs)
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 2 }}>
            {groups.length === 0 && <span className="muted">Aucun groupe créé</span>}
            {groups.map((g) => (
              <label key={g.id} style={{ flexDirection: "row", alignItems: "center", gap: 8, fontWeight: 400 }}>
                <input
                  type="checkbox"
                  style={{ width: "auto" }}
                  checked={groupeIds.includes(g.id)}
                  onChange={() => toggleGroupe(g.id)}
                />
                {g.nom}
              </label>
            ))}
          </div>
        </label>

        <div className="form-grid">
          <label>
            Type de pièce d'identité
            <select value={pieceType} onChange={(e) => setPieceType(e.target.value)}>
              <option value="">Non renseigné</option>
              {Object.entries(TYPES_PIECE_IDENTITE).map(([cle, label]) => (
                <option key={cle} value={cle}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            Numéro
            <input value={pieceNumero} onChange={(e) => setPieceNumero(e.target.value)} />
          </label>
        </div>
        <div className="form-grid">
          <label>
            Organisme émetteur
            <input value={pieceOrganisme} onChange={(e) => setPieceOrganisme(e.target.value)} />
          </label>
          <label>
            Date d'expiration
            <input type="date" value={pieceExpiration} onChange={(e) => setPieceExpiration(e.target.value)} />
          </label>
        </div>
        <label>
          Scan / photo de la pièce d'identité
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {hasPiece ? (
              <span className="badge badge-success">
                <FileText size={12} /> Document enregistré
              </span>
            ) : (
              <span className="muted" style={{ fontSize: 12 }}>Aucun document joint</span>
            )}
            <input
              ref={pieceInputRef}
              type="file"
              accept="image/*,application/pdf"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) handlePieceChange(file);
              }}
            />
            <button type="button" className="btn btn-sm" onClick={() => pieceInputRef.current?.click()}>
              {hasPiece ? "Remplacer" : "Joindre"}
            </button>
          </div>
        </label>

        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
        </label>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginTop: 4 }}>
          {resetResult ? (
            <p style={{ fontSize: 13 }}>
              Mot de passe provisoire : <code style={{ fontWeight: 700 }}>{resetResult}</code>
              <span className="muted"> — communiquez-le au client, il ne sera plus affiché.</span>
            </p>
          ) : (
            <button type="button" className="btn btn-sm" onClick={handleResetPassword}>
              <KeyRound size={13} /> Générer un mot de passe provisoire
            </button>
          )}
        </div>

        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
