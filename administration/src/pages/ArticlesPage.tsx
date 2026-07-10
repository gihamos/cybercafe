import { useCallback, useEffect, useRef, useState } from "react";
import { ShoppingBag, Printer, Plus, Trash2, Image as ImageIcon, History } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
import { AuthenticatedImage } from "../components/AuthenticatedImage";
import type { Article, ArticleCategorieEntry, MouvementStockEntry, VenteArticle } from "../api/types";
import { printReceipt } from "../utils/receipt";

export default function ArticlesPage() {
  const { isAdmin, hasPermission } = usePermissions();
  const peutGererStock = hasPermission("gestion_stock");
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<ArticleCategorieEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showCategories, setShowCategories] = useState(false);
  const [imageTarget, setImageTarget] = useState<Article | null>(null);
  const [stockTarget, setStockTarget] = useState<Article | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [a, c] = await Promise.all([
        api.get<Article[]>("/article/"),
        api.get<ArticleCategorieEntry[]>("/article-categorie/"),
      ]);
      setArticles(a);
      setCategories(c);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleActif(article: Article) {
    try {
      const updated = await api.patch<Article>(`/article/${article.id}/actif?actif=${!article.actif}`);
      setArticles((prev) => prev.map((a) => (a.id === article.id ? updated : a)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDelete(article: Article) {
    if (!confirm(`Supprimer l'article « ${article.nom} » ?`)) return;
    try {
      await api.delete(`/article/${article.id}`);
      setArticles((prev) => prev.filter((a) => a.id !== article.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <ShoppingBag size={20} /> Articles
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          {isAdmin && (
            <button className="btn" onClick={() => setShowCategories(true)}>
              🏷️ Catégories
            </button>
          )}
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              <Plus size={15} /> Nouvel article
            </button>
          )}
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : articles.length === 0 ? (
          <div className="empty-state">Aucun article</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Nom</th>
                <th>Catégorie</th>
                <th>Prix</th>
                <th>Stock</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {articles.map((a) => (
                <tr key={a.id}>
                  <td>
                    {a.a_une_image ? (
                      <AuthenticatedImage
                        path={`/article/${a.id}/image`}
                        alt={a.nom}
                        style={{ width: 36, height: 36, objectFit: "cover", borderRadius: 6 }}
                      />
                    ) : (
                      <span style={{ fontSize: 20 }}>{a.categorie_emoji || "📦"}</span>
                    )}
                  </td>
                  <td>
                    <strong>{a.nom}</strong>
                    {a.description && <div className="muted">{a.description}</div>}
                  </td>
                  <td>
                    {a.categorie_nom ? (
                      <span className="badge badge-accent">
                        {a.categorie_emoji} {a.categorie_nom}
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{a.prix.toFixed(2)}€</td>
                  <td>
                    {a.stock == null ? (
                      <span className="muted">Non suivi</span>
                    ) : (
                      <span className={`badge ${a.stock_alerte != null && a.stock <= a.stock_alerte ? "badge-danger" : "badge-neutral"}`}>
                        {a.stock}
                      </span>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${a.actif ? "badge-success" : "badge-neutral"}`}>
                      {a.actif ? "Actif" : "Inactif"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      {isAdmin && (
                        <button className="btn btn-sm" onClick={() => setImageTarget(a)} title="Image">
                          <ImageIcon size={13} />
                        </button>
                      )}
                      {peutGererStock && a.stock != null && (
                        <button className="btn btn-sm" onClick={() => setStockTarget(a)}>
                          <History size={13} /> Stock
                        </button>
                      )}
                      {isAdmin && (
                        <button className="btn btn-sm" onClick={() => toggleActif(a)}>
                          {a.actif ? "Désactiver" : "Activer"}
                        </button>
                      )}
                      {isAdmin && (
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(a)}>
                          Supprimer
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <VentesRecentes />

      {showCreate && (
        <CreateArticleModal
          categories={categories}
          onClose={() => setShowCreate(false)}
          onCreated={(article) => {
            setArticles((prev) => [...prev, article]);
            setShowCreate(false);
          }}
        />
      )}

      {showCategories && (
        <CategoriesModal
          categories={categories}
          onClose={() => setShowCategories(false)}
          onChanged={load}
        />
      )}

      {imageTarget && (
        <ImageModal
          article={imageTarget}
          onClose={() => setImageTarget(null)}
          onChanged={(updated) => {
            setArticles((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
          }}
        />
      )}

      {stockTarget && (
        <StockModal
          article={stockTarget}
          onClose={() => setStockTarget(null)}
          onChanged={(updated) => {
            setArticles((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
          }}
        />
      )}
    </div>
  );
}

function CreateArticleModal({
  categories,
  onClose,
  onCreated,
}: {
  categories: ArticleCategorieEntry[];
  onClose: () => void;
  onCreated: (article: Article) => void;
}) {
  const [nom, setNom] = useState("");
  const [prix, setPrix] = useState("1.00");
  const [categorieId, setCategorieId] = useState("");
  const [description, setDescription] = useState("");
  const [suivreStock, setSuivreStock] = useState(false);
  const [stock, setStock] = useState("0");
  const [stockAlerte, setStockAlerte] = useState("5");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const article = await api.post<Article>("/article/", {
        nom,
        prix: parseFloat(prix),
        categorie_id: categorieId ? Number(categorieId) : null,
        description: description || null,
        stock: suivreStock ? Number(stock) : null,
        stock_alerte: suivreStock ? Number(stockAlerte) : null,
      });
      onCreated(article);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouvel article</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom
          <input value={nom} onChange={(e) => setNom(e.target.value)} required autoFocus />
        </label>
        <label>
          Prix (€)
          <input type="number" step="0.01" min="0" value={prix} onChange={(e) => setPrix(e.target.value)} required />
        </label>
        <label>
          Catégorie
          <select value={categorieId} onChange={(e) => setCategorieId(e.target.value)}>
            <option value="">Aucune</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.emoji} {c.nom}
              </option>
            ))}
          </select>
        </label>
        <label>
          Description
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={suivreStock} onChange={(e) => setSuivreStock(e.target.checked)} />
          Suivre le stock de cet article
        </label>
        {suivreStock && (
          <div className="form-grid">
            <label>
              Stock initial
              <input type="number" min="0" value={stock} onChange={(e) => setStock(e.target.value)} />
            </label>
            <label>
              Seuil d'alerte
              <input type="number" min="0" value={stockAlerte} onChange={(e) => setStockAlerte(e.target.value)} />
            </label>
          </div>
        )}
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

function CategoriesModal({
  categories,
  onClose,
  onChanged,
}: {
  categories: ArticleCategorieEntry[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const [nom, setNom] = useState("");
  const [emoji, setEmoji] = useState("🏷️");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/article-categorie/", { nom, emoji: emoji || null });
      setNom("");
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(c: ArticleCategorieEntry) {
    if (!confirm(`Supprimer la catégorie « ${c.nom} » ?`)) return;
    try {
      await api.delete(`/article-categorie/${c.id}`);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  const emojisSuggeres = ["🥤", "🍫", "🍪", "🍕", "☕", "🖨️", "🎮", "💾", "📎", "🎧", "🔌", "🏷️"];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} style={{ width: 420 }}>
        <h2>Catégories d'articles</h2>
        {error && <p className="error">{error}</p>}

        <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto" }}>
          {categories.length === 0 && <p className="muted">Aucune catégorie</p>}
          {categories.map((c) => (
            <div key={c.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 4px" }}>
              <span>
                {c.emoji} {c.nom} <span className="muted">({c.nb_articles})</span>
              </span>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(c)}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>

        <form onSubmit={handleAdd} style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "flex-end" }}>
          <label style={{ flex: 1 }}>
            Nouvelle catégorie
            <input value={nom} onChange={(e) => setNom(e.target.value)} required />
          </label>
          <label style={{ width: 70 }}>
            Emoji
            <input value={emoji} onChange={(e) => setEmoji(e.target.value)} maxLength={4} />
          </label>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            <Plus size={15} />
          </button>
        </form>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
          {emojisSuggeres.map((e) => (
            <button key={e} type="button" className="btn btn-sm" onClick={() => setEmoji(e)}>
              {e}
            </button>
          ))}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

function ImageModal({
  article,
  onClose,
  onChanged,
}: {
  article: Article;
  onClose: () => void;
  onChanged: (article: Article) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [version, setVersion] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleUpload(file: File) {
    setError(null);
    setSaving(true);
    try {
      const updated = await api.upload<Article>(`/article/${article.id}/image`, file);
      onChanged(updated);
      setVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'envoi");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteImage() {
    setError(null);
    setSaving(true);
    try {
      const updated = await api.delete<Article>(`/article/${article.id}/image`);
      onChanged(updated);
      setVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} style={{ width: 360 }}>
        <h2>Image de « {article.nom} »</h2>
        {error && <p className="error">{error}</p>}

        <div style={{ display: "flex", justifyContent: "center", margin: "12px 0" }}>
          {article.a_une_image ? (
            <AuthenticatedImage
              key={version}
              path={`/article/${article.id}/image`}
              alt={article.nom}
              style={{ width: 160, height: 160, objectFit: "cover", borderRadius: 10 }}
            />
          ) : (
            <div
              style={{
                width: 160, height: 160, borderRadius: 10, background: "var(--surface-2)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 48,
              }}
            >
              {article.categorie_emoji || "📦"}
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) handleUpload(file);
          }}
        />

        <div className="modal-actions">
          <button type="button" className="btn btn-primary" disabled={saving} onClick={() => fileInputRef.current?.click()}>
            {saving ? "Envoi..." : "Choisir une image"}
          </button>
          {article.a_une_image && (
            <button type="button" className="btn btn-danger" disabled={saving} onClick={handleDeleteImage}>
              Retirer
            </button>
          )}
          <button type="button" className="btn" onClick={onClose}>
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

function StockModal({
  article,
  onClose,
  onChanged,
}: {
  article: Article;
  onClose: () => void;
  onChanged: (article: Article) => void;
}) {
  const [mouvements, setMouvements] = useState<MouvementStockEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [quantite, setQuantite] = useState("10");
  const [motifEntree, setMotifEntree] = useState("");
  const [variation, setVariation] = useState("0");
  const [motifAjustement, setMotifAjustement] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [current, setCurrent] = useState(article);

  const loadMouvements = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<MouvementStockEntry[]>(`/article/${article.id}/mouvements`);
      setMouvements(data);
    } catch {
      // best-effort
    } finally {
      setLoading(false);
    }
  }, [article.id]);

  useEffect(() => {
    loadMouvements();
  }, [loadMouvements]);

  async function handleReappro(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const params = new URLSearchParams({ quantite });
      if (motifEntree.trim()) params.set("motif", motifEntree.trim());
      const updated = await api.post<Article>(`/article/${article.id}/reapprovisionner?${params}`);
      setCurrent(updated);
      onChanged(updated);
      setMotifEntree("");
      loadMouvements();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  async function handleAjustement(e: FormEvent) {
    e.preventDefault();
    const v = parseInt(variation, 10);
    if (!v) {
      setError("La variation ne peut pas être nulle");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const params = new URLSearchParams({ variation: String(v), motif: motifAjustement });
      const updated = await api.post<Article>(`/article/${article.id}/ajuster-stock?${params}`);
      setCurrent(updated);
      onChanged(updated);
      setVariation("0");
      setMotifAjustement("");
      loadMouvements();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  const TYPE_LABEL: Record<string, string> = { entree: "Entrée", vente: "Vente", ajustement: "Ajustement" };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} style={{ width: 520 }}>
        <h2>Stock de « {current.nom} »</h2>
        <p className="muted" style={{ marginTop: -6 }}>
          Niveau actuel : <strong>{current.stock}</strong>
          {current.stock_alerte != null && ` (alerte sous ${current.stock_alerte})`}
        </p>
        {error && <p className="error">{error}</p>}

        <div className="form-grid">
          <form onSubmit={handleReappro} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <strong>Réapprovisionner</strong>
            <label>
              Quantité
              <input type="number" min="1" value={quantite} onChange={(e) => setQuantite(e.target.value)} required />
            </label>
            <label>
              Motif (optionnel)
              <input value={motifEntree} onChange={(e) => setMotifEntree(e.target.value)} placeholder="Livraison fournisseur..." />
            </label>
            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
              + Ajouter au stock
            </button>
          </form>

          <form onSubmit={handleAjustement} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <strong>Ajustement d'inventaire</strong>
            <label>
              Variation (+ ou -)
              <input type="number" value={variation} onChange={(e) => setVariation(e.target.value)} required />
            </label>
            <label>
              Motif (requis)
              <input value={motifAjustement} onChange={(e) => setMotifAjustement(e.target.value)} placeholder="Casse, vol, comptage..." required />
            </label>
            <button type="submit" className="btn btn-sm" disabled={saving}>
              Appliquer la correction
            </button>
          </form>
        </div>

        <h3 style={{ marginTop: 16 }}>Historique des mouvements</h3>
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : mouvements.length === 0 ? (
          <p className="muted">Aucun mouvement enregistré</p>
        ) : (
          <div style={{ maxHeight: 220, overflowY: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Variation</th>
                  <th>Stock après</th>
                  <th>Motif</th>
                  <th>Par</th>
                </tr>
              </thead>
              <tbody>
                {mouvements.map((m) => (
                  <tr key={m.id}>
                    <td className="muted">{new Date(m.date_mouvement).toLocaleString()}</td>
                    <td>{TYPE_LABEL[m.type_mouvement] || m.type_mouvement}</td>
                    <td className={m.variation > 0 ? "" : "error"}>
                      {m.variation > 0 ? `+${m.variation}` : m.variation}
                    </td>
                    <td>{m.stock_apres}</td>
                    <td className="muted">{m.motif || "—"}</td>
                    <td className="muted">{m.operateur_nom || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

function VentesRecentes() {
  const [ventes, setVentes] = useState<VenteArticle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<VenteArticle[]>("/article/ventes/liste?limit=20")
      .then(setVentes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function handlePrint(v: VenteArticle) {
    printReceipt({
      sousTitre: "Reçu de vente",
      lignes: [
        { label: "Article", value: v.article_nom || `#${v.article_id}` },
        { label: "Client", value: v.user_nom || "Anonyme" },
        { label: "Vendu par", value: v.operateur_nom || "—" },
        { label: "Date", value: new Date(v.date_achat).toLocaleString() },
      ],
      total: v.prix,
      reference: `Reçu #${v.id}`,
    });
  }

  return (
    <div className="card">
      <h2>Ventes récentes</h2>
      {loading ? (
        <p className="muted">Chargement...</p>
      ) : ventes.length === 0 ? (
        <div className="empty-state">Aucune vente enregistrée</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Article</th>
              <th>Client</th>
              <th>Prix</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {ventes.map((v) => (
              <tr key={v.id}>
                <td>{v.article_nom}</td>
                <td className="muted">{v.user_nom || "Anonyme"}</td>
                <td>{v.prix.toFixed(2)}€</td>
                <td className="muted">{new Date(v.date_achat).toLocaleString()}</td>
                <td>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <button className="btn btn-sm" onClick={() => handlePrint(v)}>
                      <Printer size={13} /> Reçu
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
