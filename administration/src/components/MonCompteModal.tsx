import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

interface MonProfil {
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  address: string | null;
}

export default function MonCompteModal({ onClose }: { onClose: () => void }) {
  const { user } = useAuth();
  const [profil, setProfil] = useState<MonProfil | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get<MonProfil[]>(`/user/${user.username}`)
      .then((data) => {
        const p = data[0];
        setProfil(p);
        setFirstName(p.first_name ?? "");
        setLastName(p.last_name ?? "");
        setEmail(p.email ?? "");
        setAddress(p.address ?? "");
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, [user]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    setError(null);
    setSuccess(false);
    setSaving(true);
    try {
      const params = new URLSearchParams();
      params.set("first_name", firstName);
      params.set("last_name", lastName);
      params.set("email", email);
      params.set("address", address);
      if (password.trim()) params.set("password", password.trim());
      // Particularité de l'API : PATCH /user/{username} lit ses champs dans la query
      // string, pas dans le corps JSON (comportement existant du backend, voir ClientsPage).
      await api.patch(`/user/${user.username}?${params.toString()}`);
      setSuccess(true);
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Mon compte</h2>
        {error && <p className="error">{error}</p>}
        {success && <p style={{ color: "var(--good)" }}>Compte mis à jour avec succès.</p>}

        {loading || !profil ? (
          <p className="muted">Chargement...</p>
        ) : (
          <>
            <label>
              Nom d'utilisateur
              <input value={profil.username} disabled />
            </label>
            <label>
              Prénom
              <input value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
            </label>
            <label>
              Nom
              <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </label>
            <label>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label>
              Adresse
              <input value={address} onChange={(e) => setAddress(e.target.value)} />
            </label>
            <label>
              Nouveau mot de passe (laisser vide pour ne pas changer)
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
          </>
        )}

        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving || loading}>
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Fermer
          </button>
        </div>
      </form>
    </div>
  );
}
