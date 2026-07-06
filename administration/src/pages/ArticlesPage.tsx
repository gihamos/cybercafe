import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Article } from "../api/types";

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Article[]>("/article/");
      setArticles(data);
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
        <h1>Articles</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nouvel article
        </button>
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
                  <td className="muted">{a.categorie || "—"}</td>
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

      {showCreate && (
        <CreateArticleModal
          onClose={() => setShowCreate(false)}
          onCreated={(article) => {
            setArticles((prev) => [...prev, article]);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}

function CreateArticleModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (article: Article) => void;
}) {
  const [nom, setNom] = useState("");
  const [prix, setPrix] = useState("1.00");
  const [categorie, setCategorie] = useState("");
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
        categorie: categorie || null,
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
          <input value={categorie} onChange={(e) => setCategorie(e.target.value)} placeholder="boisson, snack..." />
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
