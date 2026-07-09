import { useCallback, useEffect, useState } from "react";
import { Percent } from "lucide-react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Article, Offre, Promotion } from "../api/types";

const MECANISMES_BASE = ["pourcentage", "montant_fixe"];

function mecanismeLabel(mecanisme: string): string {
  if (mecanisme === "pourcentage") return "Pourcentage";
  if (mecanisme === "montant_fixe") return "Montant fixe";
  return mecanisme; // mécanisme personnalisé : on affiche sa clé telle quelle
}

export default function PromotionsPage() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [offres, setOffres] = useState<Offre[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [mecanismes, setMecanismes] = useState<string[]>(MECANISMES_BASE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [promos, offresData, articlesData, mecanismesData] = await Promise.all([
        api.get<Promotion[]>("/promotion/"),
        api.get<Offre[]>("/offre/"),
        api.get<Article[]>("/article/"),
        api.get<string[]>("/promotion/mecanismes"),
      ]);
      setPromotions(promos);
      setOffres(offresData);
      setArticles(articlesData);
      setMecanismes(mecanismesData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function cibleLabel(promo: Promotion): string {
    if (promo.offre_id) {
      const offre = offres.find((o) => o.id === promo.offre_id);
      return `Offre : ${offre?.nom ?? `#${promo.offre_id}`}`;
    }
    if (promo.article_id) {
      const article = articles.find((a) => a.id === promo.article_id);
      return `Article : ${article?.nom ?? `#${promo.article_id}`}`;
    }
    return "Toute la boutique";
  }

  async function toggleActif(promo: Promotion) {
    try {
      const updated = await api.patch<Promotion>(`/promotion/${promo.id}`, { actif: !promo.actif });
      setPromotions((prev) => prev.map((p) => (p.id === promo.id ? updated : p)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function handleDelete(promo: Promotion) {
    if (!confirm(`Supprimer la promotion « ${promo.nom} » ?`)) return;
    try {
      await api.delete(`/promotion/${promo.id}`);
      setPromotions((prev) => prev.filter((p) => p.id !== promo.id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          <Percent size={20} /> Promotions
        </h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nouvelle promotion
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : promotions.length === 0 ? (
          <div className="empty-state">Aucune promotion</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>Code</th>
                <th>Mécanisme</th>
                <th>S'applique à</th>
                <th>Utilisation</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {promotions.map((p) => (
                <tr key={p.id}>
                  <td>
                    <strong>{p.nom}</strong>
                  </td>
                  <td>{p.code ? <code>{p.code}</code> : <span className="muted">Automatique</span>}</td>
                  <td>
                    {mecanismeLabel(p.mecanisme)}
                    {p.mecanisme === "pourcentage" && ` (${p.valeur}%)`}
                    {p.mecanisme === "montant_fixe" && ` (${p.valeur.toFixed(2)}€)`}
                  </td>
                  <td className="muted">{cibleLabel(p)}</td>
                  <td className="muted">
                    {p.usage_count}
                    {p.usage_max != null ? ` / ${p.usage_max}` : ""}
                  </td>
                  <td>
                    <span className={`badge ${p.actif ? "badge-success" : "badge-neutral"}`}>
                      {p.actif ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <button className="btn btn-sm" onClick={() => toggleActif(p)}>
                        {p.actif ? "Désactiver" : "Activer"}
                      </button>
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p)}>
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
        <CreatePromotionModal
          offres={offres}
          articles={articles}
          mecanismes={mecanismes}
          onClose={() => setShowCreate(false)}
          onCreated={(promo) => {
            setPromotions((prev) => [promo, ...prev]);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}

function CreatePromotionModal({
  offres,
  articles,
  mecanismes,
  onClose,
  onCreated,
}: {
  offres: Offre[];
  articles: Article[];
  mecanismes: string[];
  onClose: () => void;
  onCreated: (promo: Promotion) => void;
}) {
  const [nom, setNom] = useState("");
  const [avecCode, setAvecCode] = useState(true);
  const [code, setCode] = useState("");
  const [mecanisme, setMecanisme] = useState(mecanismes[0] ?? "pourcentage");
  const [valeur, setValeur] = useState("10");
  const [cible, setCible] = useState("toutes");
  const [usageMax, setUsageMax] = useState("");
  const [parametresJson, setParametresJson] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const estMecanismePersonnalise = !MECANISMES_BASE.includes(mecanisme);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    let parametres: Record<string, unknown> | null = null;
    if (parametresJson.trim()) {
      try {
        parametres = JSON.parse(parametresJson);
      } catch {
        setError("Paramètres : JSON invalide");
        return;
      }
    }

    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        nom,
        mecanisme,
        valeur: parseFloat(valeur),
        code: avecCode ? code.trim().toUpperCase() : null,
        usage_max: usageMax ? parseInt(usageMax, 10) : null,
        parametres,
      };
      if (cible.startsWith("offre:")) payload.offre_id = parseInt(cible.split(":")[1], 10);
      if (cible.startsWith("article:")) payload.article_id = parseInt(cible.split(":")[1], 10);

      const promo = await api.post<Promotion>("/promotion/", payload);
      onCreated(promo);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Nouvelle promotion</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Nom
          <input value={nom} onChange={(e) => setNom(e.target.value)} required autoFocus />
        </label>

        <label>
          <input
            type="checkbox"
            checked={avecCode}
            onChange={(e) => setAvecCode(e.target.checked)}
            style={{ width: "auto", marginRight: 6 }}
          />
          Nécessite un code promo (sinon appliquée automatiquement)
        </label>
        {avecCode && (
          <label>
            Code
            <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} required placeholder="ex: SNACK30" />
          </label>
        )}

        <div className="form-grid">
          <label>
            Mécanisme
            <select value={mecanisme} onChange={(e) => setMecanisme(e.target.value)}>
              {mecanismes.map((m) => (
                <option key={m} value={m}>
                  {mecanismeLabel(m)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Valeur {mecanisme === "pourcentage" ? "(%)" : mecanisme === "montant_fixe" ? "(€)" : ""}
            <input type="number" step="0.01" min="0" value={valeur} onChange={(e) => setValeur(e.target.value)} required />
          </label>
        </div>

        {estMecanismePersonnalise && (
          <label>
            Paramètres (JSON, propres à ce mécanisme)
            <textarea
              value={parametresJson}
              onChange={(e) => setParametresJson(e.target.value)}
              placeholder='ex: {"heure_debut": 18, "heure_fin": 20}'
              rows={3}
            />
          </label>
        )}

        <label>
          S'applique à
          <select value={cible} onChange={(e) => setCible(e.target.value)}>
            <option value="toutes">Toute la boutique</option>
            <optgroup label="Une offre spécifique">
              {offres.map((o) => (
                <option key={`offre:${o.id}`} value={`offre:${o.id}`}>
                  {o.nom}
                </option>
              ))}
            </optgroup>
            <optgroup label="Un article spécifique">
              {articles.map((a) => (
                <option key={`article:${a.id}`} value={`article:${a.id}`}>
                  {a.nom}
                </option>
              ))}
            </optgroup>
          </select>
        </label>

        <label>
          Nombre d'utilisations max (optionnel)
          <input
            type="number"
            min="1"
            value={usageMax}
            onChange={(e) => setUsageMax(e.target.value)}
            placeholder="Illimité"
          />
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
