import { useCallback, useEffect, useState } from "react";
import { Wallet, Banknote, CreditCard, Smartphone, Landmark, Gift, Ticket as TicketIcon, RefreshCw } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type {
  Article,
  CaisseResume,
  CaisseSession,
  CaisseTransaction,
  ClientUser,
  Offre,
  TypePaiement,
} from "../api/types";

const PAIEMENT_ICON: Record<string, typeof Banknote> = {
  especes: Banknote,
  carte: CreditCard,
  mobile_money: Smartphone,
  virement: Landmark,
  code_prepaye: TicketIcon,
  gratuit: Gift,
  paypal: CreditCard,
};

const PAIEMENT_LABEL: Record<string, string> = {
  especes: "Espèces",
  carte: "Carte",
  mobile_money: "Mobile money",
  virement: "Virement",
  code_prepaye: "Code prépayé",
  gratuit: "Gratuit",
  paypal: "PayPal",
};

export default function CaissePage() {
  const [caisse, setCaisse] = useState<CaisseSession | null>(null);
  const [resume, setResume] = useState<CaisseResume | null>(null);
  const [transactions, setTransactions] = useState<CaisseTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCloture, setShowCloture] = useState(false);
  const [dernierEcart, setDernierEcart] = useState<CaisseSession | null>(null);
  const [dernierResume, setDernierResume] = useState<CaisseResume | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<CaisseSession | null>("/caisse/ouverte");
      setCaisse(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadActivite = useCallback(async (caisseId: number) => {
    try {
      const [r, t] = await Promise.all([
        api.get<CaisseResume>(`/caisse/${caisseId}/resume`),
        api.get<CaisseTransaction[]>(`/caisse/${caisseId}/transactions`),
      ]);
      setResume(r);
      setTransactions(t);
    } catch {
      // best-effort : l'écran reste utilisable même si la ventilation ne charge pas
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (caisse) loadActivite(caisse.id);
  }, [caisse, loadActivite]);

  if (loading) {
    return (
      <div className="page">
        <h1>
          <Wallet size={20} /> Caisse
        </h1>
        <p className="muted">Chargement...</p>
      </div>
    );
  }

  if (!caisse) {
    return (
      <div className="page">
        <h1>
          <Wallet size={20} /> Caisse
        </h1>
        {error && <p className="error">{error}</p>}
        {dernierEcart && (
          <div className="card">
            <h3>Dernière clôture</h3>
            <p>
              Théorique : {dernierEcart.montant_cloture_theorique?.toFixed(2)}€ — Réel :{" "}
              {dernierEcart.montant_cloture_reel?.toFixed(2)}€ —{" "}
              <strong className={dernierEcart.ecart === 0 ? "" : "error"}>
                Écart : {dernierEcart.ecart != null && dernierEcart.ecart > 0 ? "+" : ""}
                {dernierEcart.ecart?.toFixed(2)}€
              </strong>
            </p>
            {dernierResume && Object.keys(dernierResume.ventilation).length > 0 && (
              <div className="stat-tiles" style={{ marginTop: 12 }}>
                {Object.entries(dernierResume.ventilation).map(([type, v]) => (
                  <VentilationTile key={type} type={type} entry={v} />
                ))}
              </div>
            )}
          </div>
        )}
        <OuvrirCaisseForm onOuverte={setCaisse} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Wallet size={20} /> Caisse
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="muted">
            Ouverte depuis {new Date(caisse.date_ouverture).toLocaleTimeString()} — fond {caisse.montant_ouverture.toFixed(2)}€
          </span>
          <button className="btn btn-sm" onClick={() => loadActivite(caisse.id)} title="Rafraîchir">
            <RefreshCw size={14} />
          </button>
          <button className="btn" onClick={() => setShowCloture(true)}>
            Clôturer la caisse
          </button>
        </div>
      </div>

      {resume && (
        <div className="stat-tiles">
          <div className="stat-tile">
            <span className="stat-tile-label">Total encaissé</span>
            <span className="stat-tile-value">{resume.total_general.toFixed(2)}€</span>
            <span className="stat-tile-sub">{resume.nb_transactions} transaction(s)</span>
          </div>
          {Object.entries(resume.ventilation).map(([type, v]) => (
            <VentilationTile key={type} type={type} entry={v} />
          ))}
        </div>
      )}

      <div className="grid-2col">
        <VenteRapide onVente={() => loadActivite(caisse.id)} />
        <EncaissementDirect onEncaisse={() => loadActivite(caisse.id)} />
      </div>

      <TransactionFeed transactions={transactions} />

      {showCloture && (
        <ClotureModal
          caisse={caisse}
          resume={resume}
          onClose={() => setShowCloture(false)}
          onCloturee={(closed) => {
            setDernierEcart(closed);
            setDernierResume(resume);
            setCaisse(null);
            setShowCloture(false);
          }}
        />
      )}
    </div>
  );
}

function OuvrirCaisseForm({ onOuverte }: { onOuverte: (caisse: CaisseSession) => void }) {
  const [montant, setMontant] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const caisse = await api.post<CaisseSession>("/caisse/ouvrir", { montant_ouverture: parseFloat(montant) });
      onOuverte(caisse);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'ouverture");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit} style={{ maxWidth: 360, display: "flex", flexDirection: "column", gap: 14 }}>
      <h2>Ouvrir la caisse</h2>
      {error && <p className="error">{error}</p>}
      <label>
        Fond de caisse de départ (€)
        <input type="number" step="0.01" min="0" value={montant} onChange={(e) => setMontant(e.target.value)} required autoFocus />
      </label>
      <button type="submit" className="btn btn-primary" disabled={saving}>
        {saving ? "Ouverture..." : "Ouvrir la caisse"}
      </button>
    </form>
  );
}

function ClotureModal({
  caisse,
  resume,
  onClose,
  onCloturee,
}: {
  caisse: CaisseSession;
  resume: CaisseResume | null;
  onClose: () => void;
  onCloturee: (caisse: CaisseSession) => void;
}) {
  const [montantReel, setMontantReel] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const closed = await api.post<CaisseSession>(`/caisse/${caisse.id}/cloturer`, {
        montant_cloture_reel: parseFloat(montantReel),
        notes: notes || null,
      });
      onCloturee(closed);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la clôture");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Clôturer la caisse</h2>
        {error && <p className="error">{error}</p>}
        <p className="muted">
          Comptez le tiroir-caisse et saisissez le montant réel. L'écart avec le montant théorique (fond +
          espèces encaissées) sera calculé automatiquement — seules les espèces affectent le tiroir physique.
        </p>
        {resume && Object.keys(resume.ventilation).length > 0 && (
          <div className="stat-tiles" style={{ marginBottom: 4 }}>
            {Object.entries(resume.ventilation).map(([type, v]) => (
              <VentilationTile key={type} type={type} entry={v} />
            ))}
          </div>
        )}
        <label>
          Montant réel compté (€)
          <input
            type="number"
            step="0.01"
            min="0"
            value={montantReel}
            onChange={(e) => setMontantReel(e.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          Notes (optionnel)
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Clôture..." : "Clôturer"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}

function VenteRapide({ onVente }: { onVente: () => void }) {
  const [type, setType] = useState<"article" | "offre">("article");
  const [articles, setArticles] = useState<Article[]>([]);
  const [offres, setOffres] = useState<Offre[]>([]);
  const [itemId, setItemId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [clients, setClients] = useState<ClientUser[]>([]);
  const [selectedClient, setSelectedClient] = useState<ClientUser | null>(null);
  const [typePaiement, setTypePaiement] = useState<TypePaiement>("especes");
  const [codePromo, setCodePromo] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get<Article[]>("/article/?actif=true").then(setArticles).catch(() => {});
    api.get<Offre[]>("/offre/?is_actif=true").then(setOffres).catch(() => {});
  }, []);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!search.trim()) return;
    try {
      const data = await api.get<ClientUser[]>(`/user/query/clients?username=${encodeURIComponent(search.trim())}`);
      setClients(data);
    } catch {
      setClients([]);
    }
  }

  async function handleVendre() {
    if (!selectedClient || !itemId) return;
    setError(null);
    setResult(null);
    setSaving(true);
    try {
      if (type === "article") {
        const params = new URLSearchParams({ user_id: String(selectedClient.id), type_paiement: typePaiement });
        if (codePromo.trim()) params.set("code_promo", codePromo.trim());
        const data = await api.post<{ prix: number; article: string }>(`/article/${itemId}/acheter?${params}`);
        setResult(`Vente enregistrée : ${data.article} — ${data.prix.toFixed(2)}€`);
      } else {
        const payload: Record<string, unknown> = {
          user_id: selectedClient.id,
          offre_id: itemId,
          type_paiement: typePaiement,
        };
        if (codePromo.trim()) payload.code_promo = codePromo.trim();
        await api.post("/abonnement/souscrire", payload);
        setResult("Abonnement souscrit avec succès.");
      }
      setItemId(null);
      setCodePromo("");
      onVente();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la vente");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <h2>Vente rapide</h2>

      <div className="form-grid" style={{ marginBottom: 14 }}>
        <label>
          Client
          {selectedClient ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="badge badge-success">{selectedClient.username}</span>
              <button type="button" className="btn btn-sm" onClick={() => setSelectedClient(null)}>
                Changer
              </button>
            </div>
          ) : (
            <form onSubmit={handleSearch} style={{ display: "flex", gap: 6 }}>
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher..." />
              <button type="submit" className="btn btn-sm">
                Chercher
              </button>
            </form>
          )}
        </label>
      </div>

      {!selectedClient && clients.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: "0 0 14px" }}>
          {clients.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className="btn btn-sm"
                style={{ marginBottom: 4 }}
                onClick={() => {
                  setSelectedClient(c);
                  setClients([]);
                }}
              >
                {c.username} ({c.email})
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="form-grid">
        <label>
          Type de produit
          <select value={type} onChange={(e) => { setType(e.target.value as "article" | "offre"); setItemId(null); }}>
            <option value="article">Article</option>
            <option value="offre">Offre / forfait</option>
          </select>
        </label>
        <label>
          Produit
          <select value={itemId ?? ""} onChange={(e) => setItemId(e.target.value ? parseInt(e.target.value, 10) : null)}>
            <option value="">Choisir...</option>
            {type === "article"
              ? articles.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nom} — {a.prix.toFixed(2)}€
                  </option>
                ))
              : offres.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.nom} — {o.prix.toFixed(2)}€
                  </option>
                ))}
          </select>
        </label>
        <label>
          Paiement
          <select value={typePaiement} onChange={(e) => setTypePaiement(e.target.value as TypePaiement)}>
            <option value="especes">Espèces</option>
            <option value="carte">Carte</option>
            <option value="mobile_money">Mobile money</option>
            <option value="virement">Virement</option>
          </select>
        </label>
        <label>
          Code promo (optionnel)
          <input value={codePromo} onChange={(e) => setCodePromo(e.target.value.toUpperCase())} />
        </label>
      </div>

      {error && <p className="error" style={{ marginTop: 10 }}>{error}</p>}
      {result && <p style={{ marginTop: 10, color: "var(--success)" }}>{result}</p>}

      <button
        className="btn btn-primary"
        style={{ marginTop: 14 }}
        disabled={!selectedClient || !itemId || saving}
        onClick={handleVendre}
      >
        {saving ? "Vente en cours..." : "Encaisser la vente"}
      </button>
    </div>
  );
}

function VentilationTile({ type, entry }: { type: string; entry: { nombre: number; total: number } }) {
  const Icon = PAIEMENT_ICON[type] ?? Banknote;
  const label = PAIEMENT_LABEL[type] ?? type;
  return (
    <div className="stat-tile">
      <span className="stat-tile-label">
        <Icon size={14} /> {label}
      </span>
      <span className="stat-tile-value">{entry.total.toFixed(2)}€</span>
      <span className="stat-tile-sub">{entry.nombre} transaction(s)</span>
    </div>
  );
}

/** Encaissement au comptoir sans article/offre au catalogue : recharge de solde ou vente
 * ponctuelle. Passe par POST /caisse/encaisser, qui valide carte/mobile money auprès du
 * fournisseur avant d'enregistrer (voir PaiementService.encaisser_caisse côté serveur). */
function EncaissementDirect({ onEncaisse }: { onEncaisse: () => void }) {
  const [search, setSearch] = useState("");
  const [clients, setClients] = useState<ClientUser[]>([]);
  const [selectedClient, setSelectedClient] = useState<ClientUser | null>(null);
  const [montant, setMontant] = useState("");
  const [typePaiement, setTypePaiement] = useState<TypePaiement>("especes");
  const [motif, setMotif] = useState<"recharge" | "autre">("recharge");
  const [telephone, setTelephone] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!search.trim()) return;
    try {
      const data = await api.get<ClientUser[]>(`/user/query/clients?username=${encodeURIComponent(search.trim())}`);
      setClients(data);
    } catch {
      setClients([]);
    }
  }

  async function handleEncaisser() {
    const montantNum = parseFloat(montant);
    if (!selectedClient || !montantNum || montantNum <= 0) return;
    setError(null);
    setResult(null);
    setSaving(true);
    try {
      const params = new URLSearchParams({
        montant: String(montantNum),
        type_paiement: typePaiement,
        user_id: String(selectedClient.id),
        crediter_solde: String(motif === "recharge"),
      });
      if (typePaiement === "mobile_money" && telephone.trim()) params.set("numero_telephone", telephone.trim());

      await api.post(`/caisse/encaisser?${params}`);

      setResult(
        motif === "recharge"
          ? `Solde de ${selectedClient.username} rechargé de ${montantNum.toFixed(2)}€.`
          : `Encaissement de ${montantNum.toFixed(2)}€ enregistré.`
      );
      setMontant("");
      setTelephone("");
      onEncaisse();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'encaissement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <h2>Encaissement direct</h2>
      <p className="muted" style={{ marginTop: -6, marginBottom: 14 }}>
        Recharge de solde ou vente hors catalogue. Carte/mobile money sont validés auprès du fournisseur avant
        d'être enregistrés.
      </p>

      <div className="form-grid" style={{ marginBottom: 14 }}>
        <label>
          Client
          {selectedClient ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="badge badge-success">{selectedClient.username}</span>
              <button type="button" className="btn btn-sm" onClick={() => setSelectedClient(null)}>
                Changer
              </button>
            </div>
          ) : (
            <form onSubmit={handleSearch} style={{ display: "flex", gap: 6 }}>
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher..." />
              <button type="submit" className="btn btn-sm">
                Chercher
              </button>
            </form>
          )}
        </label>
      </div>

      {!selectedClient && clients.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: "0 0 14px" }}>
          {clients.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className="btn btn-sm"
                style={{ marginBottom: 4 }}
                onClick={() => {
                  setSelectedClient(c);
                  setClients([]);
                }}
              >
                {c.username} ({c.email})
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="form-grid">
        <label>
          Motif
          <select value={motif} onChange={(e) => setMotif(e.target.value as "recharge" | "autre")}>
            <option value="recharge">Recharge de solde</option>
            <option value="autre">Autre encaissement</option>
          </select>
        </label>
        <label>
          Montant (€)
          <input type="number" step="0.01" min="0.01" value={montant} onChange={(e) => setMontant(e.target.value)} />
        </label>
        <label>
          Paiement
          <select value={typePaiement} onChange={(e) => setTypePaiement(e.target.value as TypePaiement)}>
            <option value="especes">Espèces</option>
            <option value="carte">Carte</option>
            <option value="mobile_money">Mobile money</option>
            <option value="virement">Virement</option>
          </select>
        </label>
        {typePaiement === "mobile_money" && (
          <label>
            Numéro de téléphone
            <input value={telephone} onChange={(e) => setTelephone(e.target.value)} placeholder="06..." />
          </label>
        )}
      </div>

      {error && <p className="error" style={{ marginTop: 10 }}>{error}</p>}
      {result && <p style={{ marginTop: 10, color: "var(--good)" }}>{result}</p>}

      <button
        className="btn btn-primary"
        style={{ marginTop: 14 }}
        disabled={!selectedClient || !montant || saving}
        onClick={handleEncaisser}
      >
        {saving ? "Encaissement..." : "Encaisser"}
      </button>
    </div>
  );
}

function TransactionFeed({ transactions }: { transactions: CaisseTransaction[] }) {
  if (transactions.length === 0) {
    return (
      <div className="card">
        <h2>Transactions de la session</h2>
        <p className="muted">Aucune transaction pour l'instant.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Transactions de la session</h2>
      <table>
        <thead>
          <tr>
            <th>Heure</th>
            <th>Moyen</th>
            <th>Montant</th>
            <th>Statut</th>
            <th>Client</th>
            <th>Référence</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id}>
              <td>{new Date(t.date_paiement).toLocaleTimeString()}</td>
              <td>{PAIEMENT_LABEL[t.type_paiement] ?? t.type_paiement}</td>
              <td>{t.montant.toFixed(2)}€</td>
              <td>
                <span className={`badge ${t.statut === "succes" ? "badge-success" : t.statut === "annule" ? "badge-danger" : "badge-neutral"}`}>
                  {t.statut}
                </span>
              </td>
              <td>{t.user_id ? `#${t.user_id}` : t.ticket_id ? `ticket #${t.ticket_id}` : "—"}</td>
              <td>{t.reference ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
