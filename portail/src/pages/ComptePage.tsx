import { useState } from "react";
import type { FormEvent } from "react";
import { KeyRound, Save, UserRound } from "lucide-react";
import { api, ApiError } from "../api/client";
import { usePortalAuth } from "../auth/PortalAuth";

export default function ComptePage() {
  const { profil, rechargerProfil } = usePortalAuth();
  const [email, setEmail] = useState(profil?.email || "");
  const [firstName, setFirstName] = useState(profil?.first_name || "");
  const [lastName, setLastName] = useState(profil?.last_name || "");
  const [address, setAddress] = useState(profil?.address || "");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (password && password !== passwordConfirm) {
      setError("Les deux mots de passe ne correspondent pas");
      return;
    }

    setSaving(true);
    try {
      const params = new URLSearchParams();
      if (email !== profil?.email) params.set("email", email);
      if (firstName !== (profil?.first_name || "")) params.set("first_name", firstName);
      if (lastName !== (profil?.last_name || "")) params.set("last_name", lastName);
      if (address !== (profil?.address || "")) params.set("address", address);
      if (password) params.set("password", password);

      if ([...params.keys()].length === 0) {
        setMessage("Aucune modification à enregistrer");
      } else {
        await api.patch(`/user/${profil?.username}?${params.toString()}`);
        await rechargerProfil();
        setMessage("Modifications enregistrées !");
        setPassword("");
        setPasswordConfirm("");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="section-titre">
        <UserRound size={17} /> Mon compte
      </div>

      <div className="card" style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div
          style={{
            width: 52, height: 52, borderRadius: 16, background: "var(--accent-grad)",
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 800, fontSize: 19,
          }}
        >
          {(profil?.username || "?").slice(0, 2).toUpperCase()}
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 16 }}>{profil?.username}</div>
          <span className="muted" style={{ fontSize: 13 }}>
            Membre depuis {profil ? new Date(profil.date_create).toLocaleDateString() : "—"}
          </span>
        </div>
        <span className="badge badge-accent" style={{ marginLeft: "auto" }}>
          {profil?.solde_euros.toFixed(2)}€
        </span>
      </div>

      <form className="card fade-in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {error && <p className="error">{error}</p>}
        {message && <p className="success-box">{message}</p>}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
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
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Adresse
          <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Votre adresse postale" />
        </label>

        <div className="section-titre" style={{ marginTop: 6 }}>
          <KeyRound size={15} /> Changer de mot de passe
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label>
            Nouveau mot de passe
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Laisser vide pour conserver" autoComplete="new-password" />
          </label>
          <label>
            Confirmation
            <input type="password" value={passwordConfirm} onChange={(e) => setPasswordConfirm(e.target.value)} autoComplete="new-password" />
          </label>
        </div>

        <button className="btn btn-primary btn-block" type="submit" disabled={saving}>
          <Save size={15} /> {saving ? "Enregistrement..." : "Enregistrer"}
        </button>
      </form>
    </>
  );
}
