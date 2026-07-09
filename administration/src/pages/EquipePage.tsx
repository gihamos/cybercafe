import { useCallback, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { EquipeUser, UserRole } from "../api/types";
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
                    <span className={`badge ${m.is_active ? "badge-success" : "badge-neutral"}`}>
                      {m.is_active ? "Actif" : "Inactif"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
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
