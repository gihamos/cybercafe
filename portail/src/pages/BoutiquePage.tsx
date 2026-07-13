import { useEffect, useMemo, useState } from "react";
import { Clock, Database, Infinity as InfinityIcon, Plus, Search, ShoppingBag } from "lucide-react";
import { api } from "../api/client";
import { useCart } from "../cart/CartContext";
import { AuthenticatedImage } from "../components/AuthenticatedImage";
import type { ArticleBoutique, OffrePublique } from "../api/types";

const TYPE_ICON = { temps: Clock, data: Database, illimite: InfinityIcon };

export default function BoutiquePage() {
  const { ajouter, items } = useCart();
  const [articles, setArticles] = useState<ArticleBoutique[]>([]);
  const [offres, setOffres] = useState<OffrePublique[]>([]);
  const [recherche, setRecherche] = useState("");
  const [categorie, setCategorie] = useState("");
  const [ajoute, setAjoute] = useState<string | null>(null);

  useEffect(() => {
    api.get<ArticleBoutique[]>("/portail/articles").then(setArticles).catch(() => {});
    api.get<OffrePublique[]>("/portail/public/offres").then(setOffres).catch(() => {});
  }, []);

  const categories = useMemo(
    () => [...new Set(articles.map((a) => a.categorie_nom).filter(Boolean))] as string[],
    [articles]
  );

  const visibles = articles.filter((a) => {
    if (categorie && a.categorie_nom !== categorie) return false;
    if (recherche && !a.nom.toLowerCase().includes(recherche.toLowerCase())) return false;
    return true;
  });

  function signalAjout(cle: string) {
    setAjoute(cle);
    setTimeout(() => setAjoute(null), 900);
  }

  function qteAuPanier(type: string, id: number): number {
    return items.find((i) => i.type === type && i.id === id)?.quantite ?? 0;
  }

  return (
    <>
      <div className="section-titre">
        <ShoppingBag size={17} /> Forfaits de connexion
      </div>
      <div className="produits-grid">
        {offres.map((o) => {
          const Icone = TYPE_ICON[o.type_offre] || Clock;
          const cle = `forfait-${o.id}`;
          const qte = qteAuPanier("forfait", o.id);
          return (
            <div key={cle} className="produit-card fade-in">
              <div className="produit-visuel" style={{ color: "var(--accent)", background: "color-mix(in srgb, var(--accent) 9%, var(--surface-2))" }}>
                <Icone size={40} />
              </div>
              <div className="produit-infos">
                <span className="nom">{o.nom}</span>
                <span className="muted" style={{ fontSize: 12.5 }}>
                  {o.type_offre === "temps" && o.duree_minutes != null && `${o.duree_minutes} min de connexion`}
                  {o.type_offre === "data" && o.quota_mo != null && `${o.quota_mo} Mo de données`}
                  {o.type_offre === "illimite" && "Accès illimité"}
                </span>
                <div className="pied">
                  <span className="prix">{o.prix.toFixed(2)}€</span>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => {
                      ajouter({ type: "forfait", id: o.id, nom: o.nom, prix: o.prix });
                      signalAjout(cle);
                    }}
                  >
                    {ajoute === cle ? "Ajouté ✓" : <><Plus size={14} />{qte > 0 ? ` (${qte})` : ""}</>}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="section-titre" style={{ marginTop: 8 }}>
        <ShoppingBag size={17} /> Snacks & articles
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 180 }}>
          <Search size={15} style={{ position: "absolute", left: 12, top: 13, color: "var(--muted)" }} />
          <input
            placeholder="Rechercher un article..."
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            style={{ paddingLeft: 36 }}
          />
        </div>
        {categories.length > 0 && (
          <select value={categorie} onChange={(e) => setCategorie(e.target.value)} style={{ width: "auto" }}>
            <option value="">Toutes les catégories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        )}
      </div>

      {visibles.length === 0 ? (
        <div className="card empty-state">Aucun article trouvé</div>
      ) : (
        <div className="produits-grid">
          {visibles.map((a) => {
            const cle = `article-${a.id}`;
            const qte = qteAuPanier("article", a.id);
            return (
              <div key={cle} className="produit-card fade-in">
                <div className="produit-visuel">
                  {a.a_une_image ? (
                    <AuthenticatedImage path={`/portail/articles/${a.id}/image`} alt={a.nom} />
                  ) : (
                    <span>{a.categorie_emoji || "📦"}</span>
                  )}
                </div>
                <div className="produit-infos">
                  <span className="nom">{a.nom}</span>
                  {a.categorie_nom && (
                    <span className="badge badge-accent" style={{ alignSelf: "flex-start" }}>{a.categorie_nom}</span>
                  )}
                  <div className="pied">
                    <span className="prix">{a.prix.toFixed(2)}€</span>
                    {a.en_rupture ? (
                      <span className="badge badge-danger">Rupture</span>
                    ) : (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => {
                          ajouter({
                            type: "article", id: a.id, nom: a.nom, prix: a.prix,
                            emoji: a.categorie_emoji, a_une_image: a.a_une_image,
                          });
                          signalAjout(cle);
                        }}
                      >
                        {ajoute === cle ? "Ajouté ✓" : <><Plus size={14} />{qte > 0 ? ` (${qte})` : ""}</>}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
