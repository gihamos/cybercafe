import { useCallback, useEffect, useState } from "react";
import { ShieldCheck, KeyRound, Pencil } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { EquipeUser, PermissionsCatalogue, UserRole } from "../api/types";
import { useAuth } from "../auth/AuthContext";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrateur",
  operateur: "Opérateur",
  client: "Client",
};

export default function EquipePage() {
  const { user: currentUser } = useAuth();
  const [equipe, setEquipe] = useState<EquipeUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [permissionsTarget, setPermissionsTarget] = useState<EquipeUser | null>(null);
  const [editTarget, setEditTarget] = useState<EquipeUser | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<EquipeUser[]>("/user/equipe");
      setEquipe(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleActive(member: EquipeUser) {
    try {
      await api.patch(`/user/setupdateUser/${member.username}?active=${!member.is_active}`);
      setEquipe((prev) =>
        prev.map((m) => (m.username === member.username ? { ...m, is_active: !m.is_active } : m))
      );
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function changeRole(member: EquipeUser, role: UserRole) {
    try {
      await api.patch(`/user/updateRole/${member.username}?role=${role}`);
      setEquipe((prev) => prev.map((m) => (m.username === member.username ? { ...m, role } : m)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDelete(member: EquipeUser) {
    if (!confirm(`Supprimer le compte « ${member.username} » ?`)) return;
    try {
      await api.delete(`/user/${member.username}`);
      setEquipe((prev) => prev.filter((m) => m.username !== member.username));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <ShieldCheck size={20} /> Équipe
        </h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nouveau membre
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : equipe.length === 0 ? (
          <div className="empty-state">Aucun opérateur/admin</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Membre</th>
                <th>Rôle</th>
                <th>Permissions</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {equipe.map((m) => (
                <tr key={m.id}>
                  <td>
                    <strong>{m.username}</strong>
                    <div className="muted">{m.email}</div>
                  </td>
                  <td>
                    <select
                      value={m.role}
                      disabled={m.username === currentUser?.username}
                      onChange={(e) => changeRole(m, e.target.value as UserRole)}
                    >
                      <option value="operateur">{ROLE_LABELS.operateur}</option>
                      <option value="admin">{ROLE_LABELS.admin}</option>
                    </select>
                  </td>
                  <td>
                    {m.role === "admin" ? (
                      <span className="badge badge-accent">Accès complet</span>
                    ) : (
                      <button className="btn btn-sm" onClick={() => setPermissionsTarget(m)}>
                        <KeyRound size={13} />
                        {m.permissions === null ? "Accès complet" : `${m.permissions.length} permission(s)`}
                      </button>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${m.is_active ? "badge-success" : "badge-neutral"}`}>
                      {m.is_active ? "Actif" : "Inactif"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <button className="btn btn-sm" onClick={() => setEditTarget(m)}>
                        <Pencil size={13} /> Modifier
                      </button>
                      <button className="btn btn-sm" onClick={() => toggleActive(m)}>
                        {m.is_active ? "Désactiver" : "Activer"}
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={m.username === currentUser?.username}
                        onClick={() => handleDelete(m)}
                      >
                        Supprimer
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
        <CreateMemberModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}

      {permissionsTarget && (
        <PermissionsModal
          member={permissionsTarget}
          onClose={() => setPermissionsTarget(null)}
          onSaved={(permissions) => {
            setEquipe((prev) =>
              prev.map((m) => (m.id === permissionsTarget.id ? { ...m, permissions } : m))
            );
            setPermissionsTarget(null);
          }}
        />
      )}

      {editTarget && (
        <EditMemberModal
          member={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function EditMemberModal({
  member,
  onClose,
  onSaved,
}: {
  member: EquipeUser;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [username, setUsername] = useState(member.username);
  const [firstName, setFirstName] = useState(member.first_name || "");
  const [lastName, setLastName] = useState(member.last_name || "");
  const [email, setEmail] = useState(member.email);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const params = new URLSearchParams();
      if (username.trim() && username.trim() !== member.username) params.set("nouveau_username", username.trim());
      params.set("first_name", firstName);
      params.set("last_name", lastName);
      params.set("email", email);
      if (password.trim()) params.set("password", password.trim());
      // Particularité de l'API : PATCH /user/{username} lit ses champs dans la query
      // string, pas dans le corps JSON (comportement existant du backend).
      await api.patch(`/user/${member.username}?${params.toString()}`);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Modifier {member.username}</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom d'utilisateur
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <div className="form-grid">
          <label>
            Prénom
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </label>
          <label>
            Nom
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </label>
        </div>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Nouveau mot de passe (laisser vide pour ne pas changer)
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
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

function PermissionsModal({
  member,
  onClose,
  onSaved,
}: {
  member: EquipeUser;
  onClose: () => void;
  onSaved: (permissions: string[] | null) => void;
}) {
  const [catalogue, setCatalogue] = useState<PermissionsCatalogue>({});
  const [illimite, setIllimite] = useState(member.permissions === null);
  const [selected, setSelected] = useState<string[]>(member.permissions ?? []);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get<PermissionsCatalogue>("/user/permissions/catalogue").then(setCatalogue).catch(() => {});
  }, []);

  function toggle(cle: string) {
    setSelected((prev) => (prev.includes(cle) ? prev.filter((x) => x !== cle) : [...prev, cle]));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const permissions = illimite ? null : selected;
      await api.patch(`/user/${member.username}/permissions`, { permissions });
      onSaved(permissions);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Permissions de {member.username}</h2>
        {error && <p className="error">{error}</p>}
        <p className="muted" style={{ marginTop: -6 }}>
          Définit ce que cet opérateur a le droit de faire dans le panneau. Par défaut (accès complet),
          un opérateur peut tout faire — restreignez uniquement si nécessaire.
        </p>

        <label style={{ display: "flex", alignItems: "center", gap: 8, flexDirection: "row" }}>
          <input type="checkbox" checked={illimite} onChange={(e) => setIllimite(e.target.checked)} />
          Accès complet (aucune restriction)
        </label>

        {!illimite && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
            {Object.entries(catalogue).map(([cle, label]) => (
              <label key={cle} style={{ display: "flex", alignItems: "center", gap: 8, flexDirection: "row" }}>
                <input type="checkbox" checked={selected.includes(cle)} onChange={() => toggle(cle)} />
                {label}
              </label>
            ))}
            {Object.keys(catalogue).length === 0 && <p className="muted">Chargement du catalogue...</p>}
          </div>
        )}

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

function CreateMemberModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [role, setRole] = useState<UserRole>("operateur");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/user/createUser", {
        username,
        email,
        password,
        first_name: firstName,
        role,
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
        <h2>Nouveau membre de l'équipe</h2>
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
        <label>
          Rôle
          <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
            <option value="operateur">{ROLE_LABELS.operateur}</option>
            <option value="admin">{ROLE_LABELS.admin}</option>
          </select>
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
