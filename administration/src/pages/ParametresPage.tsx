import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Settings } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { CybercafeConfig } from "../api/types";

export default function ParametresPage() {
  const [config, setConfig] = useState<CybercafeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    api
      .get<CybercafeConfig>("/config/cybercafe")
      .then(setConfig)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, []);

  function setField<K extends keyof CybercafeConfig>(key: K, value: CybercafeConfig[K]) {
    setConfig((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function handleLogoChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setField("cybercafe.logo", reader.result as string);
    reader.readAsDataURL(file);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await api.patch<CybercafeConfig>("/config/cybercafe", config);
      setConfig(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <h1>
          <Settings size={20} /> Paramètres
        </h1>
        <p className="muted">Chargement...</p>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="page">
        <h1>
          <Settings size={20} /> Paramètres
        </h1>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="page">
      <h1>
        <Settings size={20} /> Paramètres
      </h1>
      <p className="page-subtitle">Identité du cybercafé — utilisée sur les reçus, l'écran du kiosque et le panneau.</p>

      {error && <p className="error">{error}</p>}
      {success && <p style={{ color: "var(--good)", fontSize: 13, fontWeight: 600 }}>Enregistré ✓</p>}

      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 560 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {config["cybercafe.logo"] && (
            <img
              src={config["cybercafe.logo"]}
              alt="Logo"
              style={{ width: 64, height: 64, objectFit: "contain", borderRadius: 8, border: "1px solid var(--border)" }}
            />
          )}
          <label style={{ flex: 1 }}>
            Logo
            <input type="file" accept="image/*" onChange={handleLogoChange} />
          </label>
        </div>

        <label>
          Nom du cybercafé
          <input value={config["cybercafe.nom"]} onChange={(e) => setField("cybercafe.nom", e.target.value)} required />
        </label>

        <div className="form-grid">
          <label>
            Adresse
            <input value={config["cybercafe.adresse"] || ""} onChange={(e) => setField("cybercafe.adresse", e.target.value)} />
          </label>
          <label>
            Numéro SIRET
            <input value={config["cybercafe.siret"] || ""} onChange={(e) => setField("cybercafe.siret", e.target.value)} />
          </label>
          <label>
            Téléphone
            <input value={config["cybercafe.telephone"] || ""} onChange={(e) => setField("cybercafe.telephone", e.target.value)} />
          </label>
          <label>
            Email
            <input type="email" value={config["cybercafe.email"] || ""} onChange={(e) => setField("cybercafe.email", e.target.value)} />
          </label>
          <label>
            Devise
            <input value={config["cybercafe.devise"]} onChange={(e) => setField("cybercafe.devise", e.target.value)} />
          </label>
          <label>
            Taille max. des fichiers dans le chat (Mo)
            <input
              type="number"
              min="1"
              value={config["chat.taille_max_fichier_mo"]}
              onChange={(e) => setField("chat.taille_max_fichier_mo", Number(e.target.value))}
            />
          </label>
        </div>

        <label>
          Pied de reçu (message affiché en bas des reçus imprimés)
          <input value={config["cybercafe.pied_recu"]} onChange={(e) => setField("cybercafe.pied_recu", e.target.value)} />
        </label>

        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      </form>
    </div>
  );
}
