import { useCallback, useEffect, useState } from "react";
import { ShoppingBag, Printer, Plus, Trash2 } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Article, ArticleCategorieEntry, VenteArticle } from "../api/types";
import { printReceipt } from "../utils/receipt";

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<ArticleCategorieEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showCategories, setShowCategories] = useState(false);

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
          <button className="btn" onClick={() => setShowCategories(true)}>
            🏷️ Catégories
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={15} /> Nouvel article
          </button>
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
                <th>Nom</th>
                <th>Catégorie</th>
                <th>Prix</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {articles.map((a) => (
                <tr key={a.id}>
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
                    <span className={`badge ${a.actif ? "badge-success" : "badge-neutral"}`}>
                      {a.actif ? "Actif" : "Inactif"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <button className="btn btn-sm" onClick={() => toggleActif(a)}>
                        {a.actif ? "Désactiver" : "Activer"}
                      </button>
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(a)}>
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
      titre: "Cybercafé",
      sousTitre: "Reçu de vente",
      lignes: [
        { label: "Article", value: v.article_nom || `#${v.article_id}` },
        { label: "Client", value: v.user_nom || "Anonyme" },
        { label: "Vendu par", value: v.operateur_nom || "—" },
        { label: "Date", value: new Date(v.date_achat).toLocaleString() },
      ],
      total: `${v.prix.toFixed(2)}€`,
      pied: `Reçu #${v.id}\nMerci de votre visite !`,
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
