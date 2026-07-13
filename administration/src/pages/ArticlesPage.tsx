import { useCallback, useEffect, useRef, useState } from "react";
import { ShoppingBag, Printer, Plus, Trash2, Image as ImageIcon, History, Pencil, Tags, Package } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { usePermissions } from "../auth/usePermissions";
import { AuthenticatedImage } from "../components/AuthenticatedImage";
import { BulkBar, executerActionGroupee, resumeActionGroupee, useSelection } from "../components/BulkBar";
import type { Article, ArticleCategorieEntry, MouvementStockEntry, VenteArticle } from "../api/types";
import { printReceipt } from "../utils/receipt";

export default function ArticlesPage() {
  const { isAdmin, hasPermission } = usePermissions();
  const peutGererStock = hasPermission("gestion_stock");
  const { selected, toggle, clear } = useSelection<number>();
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<ArticleCategorieEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recherche, setRecherche] = useState("");
  const [categorieFilter, setCategorieFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<Article | null>(null);
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

  const articlesSelectionnes = articles.filter((a) => selected.has(a.id));

  async function bulkActif(actif: boolean) {
    const cibles = articlesSelectionnes.filter((a) => a.actif !== actif);
    const resultat = await executerActionGroupee(cibles, (a) => api.patch(`/article/${a.id}/actif?actif=${actif}`));
    alert(resumeActionGroupee(actif ? "Activation" : "Désactivation", resultat));
    clear();
    load();
  }

  async function bulkSupprimer() {
    if (!confirm(`Supprimer ${articlesSelectionnes.length} article(s) ?`)) return;
    const resultat = await executerActionGroupee(articlesSelectionnes, (a) => api.delete(`/article/${a.id}`));
    alert(resumeActionGroupee("Suppression", resultat));
    clear();
    load();
  }

  // recherche : nom OU code-barres (scan direct dans le champ)
  const visibles = articles.filter((a) => {
    if (categorieFilter && String(a.categorie_id) !== categorieFilter) return false;
    if (recherche) {
      const q = recherche.toLowerCase().trim();
      return a.nom.toLowerCase().includes(q) || (a.code_barre || "").toLowerCase() === q;
    }
    return true;
  });

  const perime = (a: Article) => a.date_peremption != null && new Date(a.date_peremption) < new Date();

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <ShoppingBag size={20} /> Articles
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          {isAdmin && (
            <button className="btn" onClick={() => setShowCategories(true)}>
              <Tags size={15} /> Catégories
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

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          placeholder="Rechercher par nom ou scanner un code-barres..."
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          style={{ flex: 1, minWidth: 240, maxWidth: 380 }}
        />
        <select value={categorieFilter} onChange={(e) => setCategorieFilter(e.target.value)} style={{ maxWidth: 220 }}>
          <option value="">Toutes les catégories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.nom}</option>
          ))}
        </select>
      </div>

      {isAdmin && (
        <BulkBar count={articlesSelectionnes.length} onClear={clear}>
          <button className="btn btn-sm" onClick={() => bulkActif(true)}>Activer la sélection</button>
          <button className="btn btn-sm" onClick={() => bulkActif(false)}>Désactiver la sélection</button>
          <button className="btn btn-sm btn-danger" onClick={bulkSupprimer}>Supprimer la sélection</button>
        </BulkBar>
      )}

      {loading ? (
        <p className="muted">Chargement...</p>
      ) : visibles.length === 0 ? (
        <div className="card empty-state">Aucun article</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))", gap: 12 }}>
          {visibles.map((a) => (
            <div
              key={a.id}
              className="card"
              style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column", opacity: a.actif ? 1 : 0.55 }}
            >
              <div
                style={{
                  position: "relative", aspectRatio: "16/10", background: "var(--bg)",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 42,
                }}
              >
                {a.a_une_image ? (
                  <AuthenticatedImage path={`/article/${a.id}/image`} alt={a.nom} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : a.categorie_a_une_image && a.categorie_id ? (
                  <AuthenticatedImage path={`/article-categorie/${a.categorie_id}/image`} alt={a.categorie_nom || ""} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.85 }} />
                ) : (
                  <Package size={34} style={{ color: "var(--muted)" }} />
                )}
                {isAdmin && (
                  <input
                    type="checkbox"
                    checked={selected.has(a.id)}
                    onChange={() => toggle(a.id)}
                    style={{ position: "absolute", top: 8, left: 8, width: 17, height: 17 }}
                  />
                )}
                {a.stock != null && (
                  <span
                    className={`badge ${a.stock <= 0 ? "badge-danger" : a.stock_alerte != null && a.stock <= a.stock_alerte ? "badge-warning" : "badge-success"}`}
                    style={{ position: "absolute", top: 8, right: 8 }}
                  >
                    Stock : {a.stock}
                  </span>
                )}
              </div>

              <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" }}>
                  <strong style={{ fontSize: 14.5 }}>{a.nom}</strong>
                  <strong style={{ whiteSpace: "nowrap" }}>{a.prix.toFixed(2)}€</strong>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {a.categorie_nom && <span className="badge badge-accent">{a.categorie_nom}</span>}
                  {!a.actif && <span className="badge badge-neutral">Inactif</span>}
                  {a.code_barre && <span className="badge badge-neutral" title="Code-barres">{a.code_barre}</span>}
                  {a.date_peremption && (
                    <span className={`badge ${perime(a) ? "badge-danger" : "badge-warning"}`} title="Date de péremption">
                      {perime(a) ? "Périmé" : "Périme"} : {new Date(a.date_peremption).toLocaleDateString()}
                    </span>
                  )}
                </div>
                {(a.origine || a.poids_grammes != null || a.allergenes) && (
                  <div className="muted" style={{ fontSize: 12 }}>
                    {[a.origine, a.poids_grammes != null ? `${a.poids_grammes} g` : null, a.allergenes ? `Allergènes : ${a.allergenes}` : null]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                )}

                <div style={{ display: "flex", gap: 4, marginTop: "auto", flexWrap: "wrap" }}>
                  {isAdmin && (
                    <button className="btn btn-sm" onClick={() => setEditTarget(a)} title="Modifier">
                      <Pencil size={13} />
                    </button>
                  )}
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
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(a)} title="Supprimer">
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <VentesRecentes />

      {(showCreate || editTarget) && (
        <ArticleModal
          article={editTarget}
          categories={categories}
          onClose={() => {
            setShowCreate(false);
            setEditTarget(null);
          }}
          onSaved={() => {
            setShowCreate(false);
            setEditTarget(null);
            load();
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

function ArticleModal({
  article,
  categories,
  onClose,
  onSaved,
}: {
  article: Article | null;
  categories: ArticleCategorieEntry[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nom, setNom] = useState(article?.nom || "");
  const [prix, setPrix] = useState(article ? String(article.prix) : "1.00");
  const [categorieId, setCategorieId] = useState(article?.categorie_id ? String(article.categorie_id) : "");
  const [description, setDescription] = useState(article?.description || "");
  const [suivreStock, setSuivreStock] = useState(article ? article.stock != null : false);
  const [stock, setStock] = useState(article?.stock != null ? String(article.stock) : "0");
  const [stockAlerte, setStockAlerte] = useState(article?.stock_alerte != null ? String(article.stock_alerte) : "5");
  const [codeBarre, setCodeBarre] = useState(article?.code_barre || "");
  const [datePeremption, setDatePeremption] = useState(article?.date_peremption || "");
  const [origine, setOrigine] = useState(article?.origine || "");
  const [ingredients, setIngredients] = useState(article?.ingredients || "");
  const [poids, setPoids] = useState(article?.poids_grammes != null ? String(article.poids_grammes) : "");
  const [allergenes, setAllergenes] = useState(article?.allergenes || "");
  const [typeConservation, setTypeConservation] = useState<Article["type_conservation"]>(article?.type_conservation || "non_perissable");
  const [ficheOuverte, setFicheOuverte] = useState(
    Boolean(article && (article.code_barre || article.date_peremption || article.origine || article.ingredients || article.poids_grammes || article.allergenes))
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload = {
        nom,
        prix: parseFloat(prix),
        categorie_id: categorieId ? Number(categorieId) : null,
        description: description || null,
        stock: suivreStock ? Number(stock) : null,
        stock_alerte: suivreStock ? Number(stockAlerte) : null,
        code_barre: codeBarre.trim() || null,
        date_peremption: datePeremption || null,
        origine: origine.trim() || null,
        ingredients: ingredients.trim() || null,
        poids_grammes: poids ? parseFloat(poids) : null,
        allergenes: allergenes.trim() || null,
        type_conservation: typeConservation,
      };
      if (article) {
        await api.patch(`/article/${article.id}`, payload);
      } else {
        await api.post("/article/", payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit} style={{ width: 520, maxHeight: "88vh", overflowY: "auto" }}>
        <h2>{article ? `Modifier « ${article.nom} »` : "Nouvel article"}</h2>
        {error && <p className="error">{error}</p>}
        <div className="form-grid">
          <label>
            Nom
            <input value={nom} onChange={(e) => setNom(e.target.value)} required autoFocus />
          </label>
          <label>
            Prix (€)
            <input type="number" step="0.01" min="0" value={prix} onChange={(e) => setPrix(e.target.value)} required />
          </label>
        </div>
        <label>
          Catégorie
          <select value={categorieId} onChange={(e) => setCategorieId(e.target.value)}>
            <option value="">Aucune</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nom}
              </option>
            ))}
          </select>
        </label>
        <label>
          Description
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        {article?.sku && (
          <p className="muted" style={{ fontSize: 12, margin: 0 }}>
            Code unique d'identification (SKU) : <code>{article.sku}</code>
          </p>
        )}
        <label>
          Conservation
          <select value={typeConservation} onChange={(e) => setTypeConservation(e.target.value as Article["type_conservation"])}>
            <option value="non_perissable">Non périssable</option>
            <option value="perissable">Périssable</option>
            <option value="frais">Frais (jamais remboursable)</option>
          </select>
        </label>
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={suivreStock} onChange={(e) => setSuivreStock(e.target.checked)} />
          Suivre le stock de cet article
        </label>
        {suivreStock && (
          <div className="form-grid">
            <label>
              Stock {article ? "" : "initial"}
              <input type="number" min="0" value={stock} onChange={(e) => setStock(e.target.value)} />
            </label>
            <label>
              Seuil d'alerte
              <input type="number" min="0" value={stockAlerte} onChange={(e) => setStockAlerte(e.target.value)} />
            </label>
          </div>
        )}

        <button
          type="button"
          className="btn btn-sm"
          style={{ alignSelf: "flex-start" }}
          onClick={() => setFicheOuverte((v) => !v)}
        >
          {ficheOuverte ? "▾" : "▸"} Fiche produit (code-barres, péremption, origine...)
        </button>
        {ficheOuverte && (
          <>
            <div className="form-grid">
              <label>
                Code-barres
                <input value={codeBarre} onChange={(e) => setCodeBarre(e.target.value)} placeholder="Scanner ou saisir" />
              </label>
              <label>
                Date de péremption
                <input type="date" value={datePeremption} onChange={(e) => setDatePeremption(e.target.value)} />
              </label>
              <label>
                Origine
                <input value={origine} onChange={(e) => setOrigine(e.target.value)} placeholder="ex : France" />
              </label>
              <label>
                Poids (g)
                <input type="number" step="0.1" min="0" value={poids} onChange={(e) => setPoids(e.target.value)} />
              </label>
            </div>
            <label>
              Ingrédients
              <input value={ingredients} onChange={(e) => setIngredients(e.target.value)} placeholder="ex : farine, sucre, cacao..." />
            </label>
            <label>
              Allergènes
              <input value={allergenes} onChange={(e) => setAllergenes(e.target.value)} placeholder="ex : gluten, arachides" />
            </label>
          </>
        )}

        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Enregistrement..." : article ? "Enregistrer" : "Créer"}
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
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [imageTargetId, setImageTargetId] = useState<number | null>(null);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/article-categorie/", { nom });
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

  async function handleImageUpload(file: File) {
    if (imageTargetId == null) return;
    try {
      await api.upload(`/article-categorie/${imageTargetId}/image`, file);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur lors de l'envoi de l'image");
    } finally {
      setImageTargetId(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleImageDelete(c: ArticleCategorieEntry) {
    try {
      await api.delete(`/article-categorie/${c.id}/image`);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} style={{ width: 500 }}>
        <h2>Catégories d'articles</h2>
        <p className="muted" style={{ fontSize: 12.5, marginTop: -6 }}>
          Donnez une image à chaque catégorie : elle remplace l'emoji sur la boutique et sert
          de visuel par défaut aux articles sans photo.
        </p>
        {error && <p className="error">{error}</p>}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleImageUpload(e.target.files[0])}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 260, overflowY: "auto" }}>
          {categories.length === 0 && <p className="muted">Aucune catégorie</p>}
          {categories.map((c) => (
            <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 4px" }}>
              <div
                style={{
                  width: 40, height: 40, borderRadius: 8, overflow: "hidden", flexShrink: 0,
                  background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
                }}
              >
                {c.a_une_image ? (
                  <AuthenticatedImage path={`/article-categorie/${c.id}/image`} alt={c.nom} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <Package size={18} style={{ color: "var(--muted)" }} />
                )}
              </div>
              <span style={{ flex: 1 }}>
                {c.nom} <span className="muted">({c.nb_articles})</span>
              </span>
              <button
                className="btn btn-sm"
                title="Changer l'image"
                onClick={() => {
                  setImageTargetId(c.id);
                  fileInputRef.current?.click();
                }}
              >
                <ImageIcon size={13} />
              </button>
              {c.a_une_image && (
                <button className="btn btn-sm" title="Retirer l'image" onClick={() => handleImageDelete(c)}>
                  ✕
                </button>
              )}
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
          <button type="submit" className="btn btn-primary" disabled={saving}>
            <Plus size={15} />
          </button>
        </form>
        <p className="muted" style={{ fontSize: 11.5, marginTop: -4 }}>
          Ajoutez ensuite une vraie image via l'icône <ImageIcon size={11} style={{ verticalAlign: "-1px" }} /> ci-dessus.
        </p>

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
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <Package size={56} style={{ color: "var(--muted)" }} />
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

  const charger = useCallback(() => {
    api
      .get<VenteArticle[]>("/article/ventes/liste?limit=30")
      .then(setVentes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  async function changerStatut(v: VenteArticle, statut: string) {
    try {
      const updated = await api.patch<VenteArticle>(`/article/ventes/${v.id}/statut?statut=${statut}`);
      setVentes((prev) => prev.map((x) => (x.id === v.id ? updated : x)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  function handlePrint(v: VenteArticle) {
    // Reçu anonymisé : pas d'opérateur, client identifié par son nom/prénom.
    printReceipt({
      sousTitre: "Reçu de vente",
      lignes: [
        { label: "Article", value: v.article_nom || `#${v.article_id}` },
        { label: "Client", value: v.user_nom_complet || "Anonyme" },
        { label: "Date", value: new Date(v.date_achat).toLocaleString() },
      ],
      total: v.prix,
      reference: `Reçu #${v.id}`,
    });
  }

  const STATUT_COMMANDE: Record<string, { label: string; cls: string }> = {
    a_preparer: { label: "À préparer", cls: "badge-warning" },
    prete: { label: "Prête", cls: "badge-accent" },
    recuperee: { label: "Récupérée", cls: "badge-success" },
  };

  return (
    <div className="card">
      <h2>Ventes & commandes récentes</h2>
      <p className="muted" style={{ fontSize: 12.5 }}>
        Les commandes passées depuis le portail WiFi arrivent « À préparer » : faites-les avancer
        jusqu'à la remise au client.
      </p>
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
              <th>Commande</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {ventes.map((v) => {
              const st = STATUT_COMMANDE[v.statut_commande] || STATUT_COMMANDE.recuperee;
              return (
                <tr key={v.id}>
                  <td>{v.article_nom}</td>
                  <td className="muted">{v.user_nom || "Anonyme"}</td>
                  <td>{v.prix.toFixed(2)}€</td>
                  <td className="muted">{new Date(v.date_achat).toLocaleString()}</td>
                  <td>
                    <span className={`badge ${st.cls}`}>{st.label}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      {v.statut_commande === "a_preparer" && (
                        <button className="btn btn-sm" onClick={() => changerStatut(v, "prete")}>
                          Marquer prête
                        </button>
                      )}
                      {v.statut_commande === "prete" && (
                        <button className="btn btn-sm" onClick={() => changerStatut(v, "recuperee")}>
                          Remise au client
                        </button>
                      )}
                      <button className="btn btn-sm" onClick={() => handlePrint(v)}>
                        <Printer size={13} /> Reçu
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
