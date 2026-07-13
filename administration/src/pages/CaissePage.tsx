import { useCallback, useEffect, useRef, useState } from "react";
import { Wallet, Banknote, CreditCard, Smartphone, Landmark, Gift, Ticket as TicketIcon, RefreshCw, ShoppingCart, Trash2, Undo2, Printer } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError, openAuthenticatedHtml } from "../api/client";
import type {
  Article,
  CaisseResume,
  CaisseSession,
  CaisseTransaction,
  ClientUser,
  Offre,
  TypePaiement,
  VenteCaisse,
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

      <CaisseProPage onVente={() => loadActivite(caisse.id)} />

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

// ===========================================================================
// CAISSE PRO : vente groupée (scan code-barres, panier central, client
// optionnel — un client de caisse est un simple acheteur, pas forcément un
// compte wifi/poste) + remboursement total ou partiel d'un ticket de caisse.
// ===========================================================================

type TypeLignePanier = "article" | "forfait" | "bon";

interface LignePanierPro {
  cle: string;
  type: TypeLignePanier;
  id?: number;
  nom: string;
  prix: number;
  quantite: number;
  sku?: string | null;
}

function CaisseProPage({ onVente }: { onVente: () => void }) {
  const [mode, setMode] = useState<"vente" | "remboursement">("vente");

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="tabs-caisse" style={{ display: "flex", gap: 8 }}>
        <button
          className={`btn ${mode === "vente" ? "btn-primary" : ""}`}
          onClick={() => setMode("vente")}
        >
          <ShoppingCart size={15} /> Nouvelle vente
        </button>
        <button
          className={`btn ${mode === "remboursement" ? "btn-primary" : ""}`}
          onClick={() => setMode("remboursement")}
        >
          <Undo2 size={15} /> Remboursement
        </button>
      </div>

      {mode === "vente" ? <VentePro onVente={onVente} /> : <RemboursementPro onRembourse={onVente} />}
    </div>
  );
}

function VentePro({ onVente }: { onVente: () => void }) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [offres, setOffres] = useState<Offre[]>([]);
  const [scan, setScan] = useState("");
  const [suggestions, setSuggestions] = useState<{ type: TypeLignePanier; id: number; nom: string; prix: number; sku?: string | null }[]>([]);
  const [lignes, setLignes] = useState<LignePanierPro[]>([]);
  const [montantBon, setMontantBon] = useState("10");

  const [clientSearch, setClientSearch] = useState("");
  const [clients, setClients] = useState<ClientUser[]>([]);
  const [selectedClient, setSelectedClient] = useState<ClientUser | null>(null);

  const [typePaiement, setTypePaiement] = useState<TypePaiement>("especes");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [venteConfirmee, setVenteConfirmee] = useState<VenteCaisse | null>(null);

  const scanRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    api.get<Article[]>("/article/?actif=true").then(setArticles).catch(() => {});
    api.get<Offre[]>("/offre/?is_actif=true").then(setOffres).catch(() => {});
  }, []);

  useEffect(() => {
    scanRef.current?.focus();
  }, [venteConfirmee]);

  // Suggestions en direct : nom, SKU ou code-barres — un lecteur de code-barres
  // se comporte comme un clavier ultra-rapide suivi d'Entrée (voir handleScanSubmit).
  useEffect(() => {
    const q = scan.trim().toLowerCase();
    if (!q) {
      setSuggestions([]);
      return;
    }
    const matchArticles = articles
      .filter((a) => a.nom.toLowerCase().includes(q) || a.code_barre === scan.trim() || a.sku?.toLowerCase() === q)
      .slice(0, 6)
      .map((a) => ({ type: "article" as const, id: a.id, nom: a.nom, prix: a.prix, sku: a.sku }));
    const matchOffres = offres
      .filter((o) => o.nom.toLowerCase().includes(q))
      .slice(0, 4)
      .map((o) => ({ type: "forfait" as const, id: o.id, nom: `Forfait ${o.nom}`, prix: o.prix }));
    setSuggestions([...matchArticles, ...matchOffres]);
  }, [scan, articles, offres]);

  function ajouterLigne(type: TypeLignePanier, id: number | undefined, nom: string, prix: number, sku?: string | null) {
    setLignes((prev) => {
      const cle = `${type}-${id ?? nom}`;
      const existante = prev.find((l) => l.cle === cle);
      if (existante && type !== "bon") {
        return prev.map((l) => (l.cle === cle ? { ...l, quantite: l.quantite + 1 } : l));
      }
      return [...prev, { cle: type === "bon" ? `bon-${Date.now()}` : cle, type, id, nom, prix, quantite: 1, sku }];
    });
    setScan("");
    setSuggestions([]);
    scanRef.current?.focus();
  }

  function handleScanSubmit(e: FormEvent) {
    e.preventDefault();
    if (!scan.trim()) return;
    // priorité au code-barres exact scanné (correspondance stricte)
    const parCodeBarre = articles.find((a) => a.code_barre === scan.trim());
    if (parCodeBarre) {
      ajouterLigne("article", parCodeBarre.id, parCodeBarre.nom, parCodeBarre.prix, parCodeBarre.sku);
      return;
    }
    // sinon la première suggestion textuelle
    if (suggestions.length > 0) {
      const s = suggestions[0];
      ajouterLigne(s.type, s.id, s.nom, s.prix, s.sku);
      return;
    }
    setError(`Aucun produit trouvé pour « ${scan} »`);
  }

  function ajouterBon() {
    const montant = parseFloat(montantBon);
    if (!montant || montant <= 0) return;
    ajouterLigne("bon", undefined, `Bon de recharge ${montant.toFixed(2)}€`, montant);
  }

  function changerQuantite(cle: string, quantite: number) {
    setLignes((prev) =>
      quantite <= 0 ? prev.filter((l) => l.cle !== cle) : prev.map((l) => (l.cle === cle ? { ...l, quantite } : l))
    );
  }

  async function chercherClient(e: FormEvent) {
    e.preventDefault();
    if (!clientSearch.trim()) return;
    try {
      const data = await api.get<ClientUser[]>(`/user/query/clients?username=${encodeURIComponent(clientSearch.trim())}`);
      setClients(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  const total = lignes.reduce((acc, l) => acc + l.prix * l.quantite, 0);

  async function encaisser() {
    if (lignes.length === 0) return;
    setError(null);
    setSaving(true);
    try {
      const params = new URLSearchParams({ type_paiement: typePaiement });
      if (selectedClient) params.set("user_id", String(selectedClient.id));
      const vente = await api.post<VenteCaisse>(`/caisse/vente?${params.toString()}`, {
        items: lignes.map((l) => ({
          type: l.type,
          ...(l.type === "bon" ? { montant: l.prix } : { id: l.id }),
          quantite: l.quantite,
        })),
      });
      setVenteConfirmee(vente);
      setLignes([]);
      setSelectedClient(null);
      setClients([]);
      onVente();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'encaissement");
    } finally {
      setSaving(false);
    }
  }

  function imprimerTicket(reference: string) {
    openAuthenticatedHtml(`/caisse/ventes/${reference}/ticket`).catch(() => {
      alert("Impossible d'ouvrir le ticket");
    });
  }

  if (venteConfirmee) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "center", textAlign: "center", padding: "20px 0" }}>
        <span className="badge badge-success" style={{ fontSize: 14 }}>Vente encaissée</span>
        <div style={{ fontSize: 22, fontWeight: 800 }}>{venteConfirmee.total.toFixed(2)}€</div>
        <code style={{ fontSize: 15, letterSpacing: "0.1em" }}>{venteConfirmee.reference}</code>
        {venteConfirmee.lignes.some((l) => l.ticket_code) && (
          <div className="muted" style={{ fontSize: 13 }}>
            {venteConfirmee.lignes.filter((l) => l.ticket_code).map((l) => (
              <div key={l.id}>{l.designation} : <code>{l.ticket_code}</code></div>
            ))}
          </div>
        )}
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-primary" onClick={() => imprimerTicket(venteConfirmee.reference)}>
            <Printer size={15} /> Imprimer le ticket
          </button>
          <button className="btn" onClick={() => setVenteConfirmee(null)}>
            Nouvelle vente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 20 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <form onSubmit={handleScanSubmit} style={{ position: "relative" }}>
          <input
            ref={scanRef}
            autoFocus
            value={scan}
            onChange={(e) => setScan(e.target.value)}
            placeholder="Scanner un code-barres, ou saisir un nom / SKU..."
            style={{ fontSize: 15, padding: "12px 14px" }}
          />
          {suggestions.length > 0 && (
            <div className="card" style={{ position: "absolute", top: "100%", left: 0, right: 0, zIndex: 10, padding: 4, marginTop: 4 }}>
              {suggestions.map((s) => (
                <button
                  key={`${s.type}-${s.id}`}
                  type="button"
                  className="btn btn-sm"
                  style={{ width: "100%", justifyContent: "space-between", marginBottom: 2 }}
                  onClick={() => ajouterLigne(s.type, s.id, s.nom, s.prix, s.sku)}
                >
                  <span>
                    {s.type === "forfait" ? "📶 " : ""}{s.nom} {s.sku && <span className="muted">({s.sku})</span>}
                  </span>
                  <strong>{s.prix.toFixed(2)}€</strong>
                </button>
              ))}
            </div>
          )}
        </form>

        <div className="card" style={{ display: "flex", gap: 8, alignItems: "flex-end", padding: 12 }}>
          <label style={{ flex: 1, margin: 0 }}>
            Bon de recharge (coupon) — montant
            <input type="number" min="1" step="0.5" value={montantBon} onChange={(e) => setMontantBon(e.target.value)} />
          </label>
          <button type="button" className="btn" onClick={ajouterBon}>
            <TicketIcon size={14} /> Ajouter au panier
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        <div className="card" style={{ flex: 1, padding: 0, overflow: "hidden" }}>
          {lignes.length === 0 ? (
            <div className="empty-state">Panier vide — scannez ou recherchez un produit</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Produit</th>
                  <th>Qté</th>
                  <th>Prix</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lignes.map((l) => (
                  <tr key={l.cle}>
                    <td>
                      {l.nom}
                      {l.sku && <div className="muted" style={{ fontSize: 11 }}>{l.sku}</div>}
                    </td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        value={l.quantite}
                        onChange={(e) => changerQuantite(l.cle, Math.max(0, Number(e.target.value)))}
                        style={{ width: 60 }}
                      />
                    </td>
                    <td>{(l.prix * l.quantite).toFixed(2)}€</td>
                    <td>
                      <button className="btn btn-sm" onClick={() => changerQuantite(l.cle, 0)}>
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <strong style={{ fontSize: 13 }}>Client (optionnel)</strong>
          <p className="muted" style={{ fontSize: 12, margin: 0 }}>
            Un client de caisse est un simple acheteur — laissez vide pour une vente anonyme.
          </p>
          {selectedClient ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="badge badge-accent">{selectedClient.username}</span>
              <span className="muted" style={{ fontSize: 12 }}>solde {selectedClient.solde_euros.toFixed(2)}€</span>
              <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={() => setSelectedClient(null)}>
                Retirer
              </button>
            </div>
          ) : (
            <>
              <form onSubmit={chercherClient} style={{ display: "flex", gap: 6 }}>
                <input placeholder="Nom d'utilisateur..." value={clientSearch} onChange={(e) => setClientSearch(e.target.value)} />
                <button type="submit" className="btn btn-sm">Chercher</button>
              </form>
              {clients.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 120, overflowY: "auto" }}>
                  {clients.slice(0, 6).map((c) => (
                    <button
                      key={c.id}
                      className="btn btn-sm"
                      style={{ justifyContent: "flex-start" }}
                      onClick={() => {
                        setSelectedClient(c);
                        setClients([]);
                        setClientSearch("");
                      }}
                    >
                      {c.username} — {c.solde_euros.toFixed(2)}€
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
            <span className="muted">Articles</span>
            <span>{lignes.reduce((a, l) => a + l.quantite, 0)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 22, fontWeight: 800 }}>
            <span>Total</span>
            <span>{total.toFixed(2)}€</span>
          </div>
          <label style={{ margin: 0 }}>
            Moyen de paiement
            <select value={typePaiement} onChange={(e) => setTypePaiement(e.target.value as TypePaiement)}>
              <option value="especes">Espèces</option>
              <option value="carte">Carte</option>
              <option value="mobile_money">Mobile money</option>
              <option value="virement">Virement</option>
            </select>
          </label>
          <button className="btn btn-primary btn-lg" onClick={encaisser} disabled={saving || lignes.length === 0}>
            {saving ? "Encaissement..." : `Encaisser ${total.toFixed(2)}€`}
          </button>
        </div>
      </div>
    </div>
  );
}

function RemboursementPro({ onRembourse }: { onRembourse: () => void }) {
  const [reference, setReference] = useState("");
  const [vente, setVente] = useState<VenteCaisse | null>(null);
  const [quantites, setQuantites] = useState<Record<number, number>>({});
  const [surSolde, setSurSolde] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resultat, setResultat] = useState<{ montant_rembourse: number; statut: string } | null>(null);

  async function chercher(e: FormEvent) {
    e.preventDefault();
    if (!reference.trim()) return;
    setError(null);
    setResultat(null);
    setLoading(true);
    try {
      const v = await api.get<VenteCaisse>(`/caisse/ventes/${reference.trim().toUpperCase()}`);
      setVente(v);
      setQuantites({});
    } catch (err) {
      setVente(null);
      setError(err instanceof ApiError ? err.message : "Ticket introuvable");
    } finally {
      setLoading(false);
    }
  }

  async function rembourser() {
    if (!vente) return;
    const lignesDemandees = Object.entries(quantites)
      .filter(([, q]) => q > 0)
      .map(([ligne_id, quantite]) => ({ ligne_id: Number(ligne_id), quantite }));
    if (lignesDemandees.length === 0) {
      setError("Sélectionnez au moins un produit à rembourser");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await api.post<{ montant_rembourse: number; statut: string }>(
        `/caisse/ventes/${vente.reference}/rembourser?rembourser_sur_solde=${surSolde}`,
        { lignes: lignesDemandees }
      );
      setResultat(res);
      setVente(null);
      setReference("");
      onRembourse();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors du remboursement");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <form onSubmit={chercher} style={{ display: "flex", gap: 8 }}>
        <input
          autoFocus
          value={reference}
          onChange={(e) => setReference(e.target.value.toUpperCase())}
          placeholder="Scanner ou saisir la référence du ticket de caisse..."
          style={{ fontSize: 15, letterSpacing: "0.08em" }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          Rechercher
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {resultat && (
        <p className="success-box" style={{ padding: "10px 14px", borderRadius: 8, background: "var(--accent-bg)" }}>
          Remboursement de {resultat.montant_rembourse.toFixed(2)}€ effectué ({resultat.statut}).
        </p>
      )}

      {vente && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <strong>{vente.reference}</strong>
              <div className="muted" style={{ fontSize: 12 }}>
                {new Date(vente.date_vente).toLocaleString()} — {vente.user_nom || "Client de passage"}
              </div>
            </div>
            <span className={`badge ${vente.statut === "payee" ? "badge-success" : vente.statut === "remboursee" ? "badge-neutral" : "badge-warning"}`}>
              {vente.statut === "payee" ? "Payé" : vente.statut === "remboursee" ? "Remboursé" : "Partiellement remboursé"}
            </span>
          </div>

          <table>
            <thead>
              <tr>
                <th>Produit</th>
                <th>Prix unit.</th>
                <th>Acheté</th>
                <th>Déjà remb.</th>
                <th>À rembourser</th>
              </tr>
            </thead>
            <tbody>
              {vente.lignes.map((l) => {
                const restant = l.quantite - l.quantite_remboursee;
                return (
                  <tr key={l.id}>
                    <td>
                      {l.designation}
                      {l.produit_frais && <span className="badge badge-danger" style={{ marginLeft: 6 }}>Frais — non remboursable</span>}
                      {l.ticket_code && <div className="muted" style={{ fontSize: 11 }}>Code : {l.ticket_code}</div>}
                    </td>
                    <td>{l.prix_unitaire.toFixed(2)}€</td>
                    <td>{l.quantite}</td>
                    <td>{l.quantite_remboursee}</td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        max={restant}
                        disabled={!l.remboursable}
                        value={quantites[l.id] ?? 0}
                        onChange={(e) =>
                          setQuantites((prev) => ({ ...prev, [l.id]: Math.max(0, Math.min(restant, Number(e.target.value))) }))
                        }
                        style={{ width: 64 }}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {vente.user_id && (
            <label style={{ flexDirection: "row", alignItems: "center", gap: 8, margin: 0 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={surSolde} onChange={(e) => setSurSolde(e.target.checked)} />
              Recréditer sur le solde du compte {vente.user_nom} (sinon rendu en espèces)
            </label>
          )}

          <button className="btn btn-primary" onClick={rembourser} disabled={loading}>
            {loading ? "Traitement..." : "Valider le remboursement"}
          </button>
        </div>
      )}
    </div>
  );
}
