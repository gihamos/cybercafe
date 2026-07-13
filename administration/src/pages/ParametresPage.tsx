import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Building2, FileText, Megaphone, Network, Receipt, ScrollText, Settings, ShoppingCart, Wifi } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { CybercafeConfig } from "../api/types";

type Onglet = "etablissement" | "recus" | "caisse" | "portail" | "charte" | "annonces" | "reseau";

const ONGLETS: { id: Onglet; label: string; icon: typeof Building2; description: string }[] = [
  { id: "etablissement", label: "Établissement", icon: Building2, description: "Identité du cybercafé — reçus, kiosque, portail" },
  { id: "recus", label: "Reçus & taxes", icon: Receipt, description: "TVA, pied de reçu et fichiers du chat" },
  { id: "caisse", label: "Caisse", icon: ShoppingCart, description: "Politique de remboursement et validité des tickets de caisse" },
  { id: "portail", label: "Portail WiFi", icon: Wifi, description: "Page de garde et messages du portail client" },
  { id: "charte", label: "Charte d'utilisation", icon: ScrollText, description: "Conditions à accepter avant toute connexion" },
  { id: "annonces", label: "Annonces", icon: Megaphone, description: "Diffuser une information aux postes et au WiFi" },
  { id: "reseau", label: "Réseau & Impression", icon: Network, description: "Serveur d'impression et contrôle réseau (routeur) réels" },
];

export default function ParametresPage() {
  const [config, setConfig] = useState<CybercafeConfig | null>(null);
  const [onglet, setOnglet] = useState<Onglet>("etablissement");
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

  if (loading || !config) {
    return (
      <div className="page">
        <h1>
          <Settings size={20} /> Paramètres
        </h1>
        {error ? <p className="error">{error}</p> : <p className="muted">Chargement...</p>}
      </div>
    );
  }

  const ongletCourant = ONGLETS.find((o) => o.id === onglet)!;

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Settings size={20} /> Paramètres
        </h1>
        {onglet !== "annonces" && (
          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
            {saving ? "Enregistrement..." : success ? "Enregistré ✓" : "Enregistrer les modifications"}
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        {/* navigation latérale des sections */}
        <div className="card" style={{ width: 250, padding: 8, flexShrink: 0 }}>
          {ONGLETS.map((o) => (
            <button
              key={o.id}
              onClick={() => setOnglet(o.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10, width: "100%", textAlign: "left",
                padding: "11px 12px", borderRadius: 8, border: "none", cursor: "pointer",
                background: onglet === o.id ? "var(--accent-bg)" : "transparent",
                color: onglet === o.id ? "var(--accent)" : "var(--text)",
                fontWeight: onglet === o.id ? 700 : 500, fontSize: 14,
              }}
            >
              <o.icon size={16} /> {o.label}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <p className="muted" style={{ margin: "0 0 12px", fontSize: 13.5 }}>{ongletCourant.description}</p>

          {onglet === "etablissement" && (
            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 640 }}>
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
              </div>
            </form>
          )}

          {onglet === "recus" && (
            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 640 }}>
              <div className="form-grid">
                <label>
                  Taux de TVA (%)
                  <input
                    type="number" min="0" step="0.1"
                    value={config["cybercafe.taux_tva"]}
                    onChange={(e) => setField("cybercafe.taux_tva", Number(e.target.value))}
                  />
                </label>
                <label>
                  Taille max. des fichiers du chat (Mo)
                  <input
                    type="number" min="1"
                    value={config["chat.taille_max_fichier_mo"]}
                    onChange={(e) => setField("chat.taille_max_fichier_mo", Number(e.target.value))}
                  />
                </label>
              </div>
              <p className="muted" style={{ marginTop: -8, fontSize: 12 }}>
                Les prix des offres et articles sont déjà TTC — ce taux ne sert qu'à afficher la
                décomposition HT / TVA sur les reçus et tickets imprimés.
              </p>
              <label>
                Pied de reçu (message affiché en bas des reçus imprimés)
                <input value={config["cybercafe.pied_recu"]} onChange={(e) => setField("cybercafe.pied_recu", e.target.value)} />
              </label>
            </form>
          )}

          {onglet === "caisse" && (
            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 640 }}>
              <label>
                Validité d'un ticket de caisse (jours)
                <input
                  type="number" min="1" step="1"
                  value={config["caisse.validite_ticket_jours"]}
                  onChange={(e) => setField("caisse.validite_ticket_jours", Number(e.target.value))}
                />
              </label>
              <p className="muted" style={{ marginTop: -8, fontSize: 12 }}>
                Passé ce délai depuis la vente, un ticket de caisse ne peut plus être présenté pour un
                remboursement (total ou partiel).
              </p>
              <label>
                Politique de remboursement (affichée sur le ticket de caisse)
                <textarea
                  rows={4}
                  value={config["caisse.politique_remboursement"]}
                  onChange={(e) => setField("caisse.politique_remboursement", e.target.value)}
                  placeholder="ex : Remboursement sous 30 jours sur présentation du ticket. Produits frais non repris."
                />
              </label>
              <p className="muted" style={{ fontSize: 12, marginTop: -8 }}>
                Les produits marqués « frais » dans leur fiche article ne sont jamais remboursables,
                quelle que soit cette politique — la caisse le refuse automatiquement.
              </p>
            </form>
          )}

          {onglet === "portail" && (
            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 640 }}>
              <label>
                Titre de la page de garde
                <input
                  value={config["portail.titre_accueil"] || ""}
                  onChange={(e) => setField("portail.titre_accueil", e.target.value)}
                  placeholder="Par défaut : le nom du cybercafé"
                />
              </label>
              <label>
                Texte de la page de garde
                <textarea
                  rows={3}
                  value={config["portail.texte_accueil"] || ""}
                  onChange={(e) => setField("portail.texte_accueil", e.target.value)}
                  placeholder="ex : Bienvenue ! Connectez-vous pour profiter du WiFi."
                />
              </label>
              <label>
                Message de la page de connexion
                <textarea
                  rows={2}
                  value={config["portail.message_connexion"] || ""}
                  onChange={(e) => setField("portail.message_connexion", e.target.value)}
                  placeholder="ex : Le code ticket se trouve sur votre reçu."
                />
              </label>
              <label>
                Message d'information général (bannière visible sur tout le portail)
                <textarea
                  rows={2}
                  value={config["portail.message_info"] || ""}
                  onChange={(e) => setField("portail.message_info", e.target.value)}
                  placeholder="ex : Maintenance du réseau vendredi de 8h à 9h."
                />
              </label>
            </form>
          )}

          {onglet === "charte" && (
            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <p className="muted" style={{ fontSize: 13 }}>
                <FileText size={13} style={{ verticalAlign: "-2px" }} /> Si une charte est renseignée, chaque client devra
                l'accepter avant de se connecter — sur les postes fixes comme sur le portail WiFi. Laissez vide pour
                désactiver cette étape.
              </p>
              <label>
                Texte de la charte / conditions d'utilisation
                <textarea
                  rows={14}
                  value={config["cybercafe.charte"] || ""}
                  onChange={(e) => setField("cybercafe.charte", e.target.value)}
                  placeholder={"ex :\n1. L'accès est réservé aux clients du cybercafé.\n2. Tout usage illégal du réseau est interdit...\n"}
                  style={{ fontFamily: "monospace", fontSize: 13 }}
                />
              </label>
            </form>
          )}

          {onglet === "annonces" && <AnnonceSection />}
          {onglet === "reseau" && <ReseauImpressionSection />}
        </div>
      </div>
    </div>
  );
}

interface StatutImpression {
  gateway_actif: string;
  gateways_disponibles: string[];
  imprimantes: string[];
  erreur: string | null;
}

interface StatutReseau {
  gateway_actif: string;
  gateways_disponibles: string[];
  joignable: boolean | null;
  erreur: string | null;
}

function ReseauImpressionSection() {
  const [statutImpression, setStatutImpression] = useState<StatutImpression | null>(null);
  const [statutReseau, setStatutReseau] = useState<StatutReseau | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resynchro, setResynchro] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function charger() {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<StatutImpression>("/impression/serveur/statut"),
      api.get<StatutReseau>("/reseau/statut"),
    ])
      .then(([imp, res]) => {
        setStatutImpression(imp);
        setStatutReseau(res);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }

  useEffect(charger, []);

  async function resynchroniser() {
    setResynchro(null);
    try {
      await api.post("/reseau/sites-bloques/resynchroniser");
      setResynchro("Liste des sites bloqués renvoyée au routeur ✓");
    } catch (err) {
      setResynchro(err instanceof ApiError ? `Erreur : ${err.message}` : "Erreur");
    }
  }

  if (loading) return <p className="muted">Chargement...</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 640 }}>
      {error && <p className="error">{error}</p>}
      <p className="muted" style={{ fontSize: 12.5, marginTop: -4 }}>
        Le serveur d'impression et le routeur réseau se configurent via les variables d'environnement du
        serveur (PRINT_GATEWAY, ROUTER_GATEWAY, MIKROTIK_HOST...) — cette page n'affiche que leur état actuel.
      </p>

      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Serveur d'impression</h3>
        {statutImpression && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="form-grid">
              <label style={{ margin: 0 }}>
                Passerelle active
                <input value={statutImpression.gateway_actif} disabled />
              </label>
              <label style={{ margin: 0 }}>
                Disponibles
                <input value={statutImpression.gateways_disponibles.join(", ")} disabled />
              </label>
            </div>
            {statutImpression.erreur ? (
              <p className="error" style={{ margin: 0 }}>{statutImpression.erreur}</p>
            ) : (
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                Imprimantes détectées : {statutImpression.imprimantes.length > 0 ? statutImpression.imprimantes.join(", ") : "aucune"}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Contrôle réseau (routeur)</h3>
        {statutReseau && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="form-grid">
              <label style={{ margin: 0 }}>
                Passerelle active
                <input value={statutReseau.gateway_actif} disabled />
              </label>
              <label style={{ margin: 0 }}>
                Disponibles
                <input value={statutReseau.gateways_disponibles.join(", ")} disabled />
              </label>
            </div>
            <span className={`badge ${statutReseau.joignable ? "badge-success" : "badge-danger"}`} style={{ alignSelf: "flex-start" }}>
              {statutReseau.joignable ? "Routeur joignable" : "Routeur injoignable"}
            </span>
            {statutReseau.erreur && <p className="error" style={{ margin: 0 }}>{statutReseau.erreur}</p>}
            {resynchro && <p className="muted" style={{ margin: 0, fontSize: 13 }}>{resynchro}</p>}
            <button className="btn btn-sm" style={{ alignSelf: "flex-start" }} onClick={resynchroniser}>
              Resynchroniser les sites bloqués vers le routeur
            </button>
          </div>
        )}
      </div>

      <button className="btn" style={{ alignSelf: "flex-start" }} onClick={charger}>
        Rafraîchir
      </button>
    </div>
  );
}

function AnnonceSection() {
  const [titre, setTitre] = useState("");
  const [message, setMessage] = useState("");
  const [cible, setCible] = useState("tous");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      const params = new URLSearchParams({ titre, message, cible });
      await api.post(`/notification/broadcast?${params.toString()}`);
      setSent(true);
      setTitre("");
      setMessage("");
      setTimeout(() => setSent(false), 3000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la diffusion");
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 640 }}>
      {error && <p className="error">{error}</p>}
      {sent && <p style={{ color: "var(--good)", fontSize: 13, fontWeight: 600 }}>Annonce diffusée ✓</p>}
      <label>
        Titre
        <input value={titre} onChange={(e) => setTitre(e.target.value)} required placeholder="ex : Information" />
      </label>
      <label>
        Message
        <textarea
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          placeholder="ex : Le cybercafé fermera exceptionnellement à 18h aujourd'hui."
        />
      </label>
      <label>
        Destinataires
        <select value={cible} onChange={(e) => setCible(e.target.value)}>
          <option value="tous">Postes fixes + portail WiFi</option>
          <option value="postes">Postes fixes uniquement</option>
          <option value="wifi">Portail WiFi uniquement</option>
        </select>
      </label>
      <p className="muted" style={{ fontSize: 12.5, marginTop: -6 }}>
        Les postes connectés reçoivent l'annonce instantanément ; le portail WiFi l'affiche en bannière
        pour tous les visiteurs.
      </p>
      <div className="modal-actions">
        <button type="submit" className="btn btn-primary" disabled={sending}>
          <Megaphone size={15} /> {sending ? "Diffusion..." : "Diffuser l'annonce"}
        </button>
      </div>
    </form>
  );
}
