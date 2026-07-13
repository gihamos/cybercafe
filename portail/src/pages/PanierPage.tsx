import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Copy, Minus, Plus, ShoppingCart, Trash2, Wallet } from "lucide-react";
import { api, ApiError } from "../api/client";
import { useCart } from "../cart/CartContext";
import { usePortalAuth } from "../auth/PortalAuth";
import type { ResultatPanier } from "../api/types";

export default function PanierPage() {
  const { items, total, changerQuantite, retirer, vider } = useCart();
  const { profil, rechargerProfil } = usePortalAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [resultat, setResultat] = useState<ResultatPanier | null>(null);
  const [busy, setBusy] = useState(false);

  const soldeInsuffisant = profil != null && total > profil.solde_euros;
  const [codeCopie, setCodeCopie] = useState<string | null>(null);

  function copierCode(code: string) {
    navigator.clipboard?.writeText(code);
    setCodeCopie(code);
    setTimeout(() => setCodeCopie(null), 2000);
  }

  async function commander() {
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<ResultatPanier>("/portail/panier/commander", {
        items: items.map((i) => ({ type: i.type, id: i.id, quantite: i.quantite })),
      });
      setResultat(res);
      vider();
      await rechargerProfil();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la commande");
    } finally {
      setBusy(false);
    }
  }

  if (resultat) {
    return (
      <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 14, textAlign: "center" }}>
        <span className="badge badge-success" style={{ alignSelf: "center" }}>Commande confirmée</span>
        <h2 style={{ fontSize: 18 }}>Merci pour votre achat !</h2>
        <div className="liste" style={{ textAlign: "left" }}>
          {resultat.lignes.map((l, i) => (
            <div className="liste-item" key={i}>
              <span>
                {l.nom} <span className="muted">× {l.quantite}</span>
              </span>
              <strong>{(l.prix_unitaire * l.quantite).toFixed(2)}€</strong>
            </div>
          ))}
          <div className="liste-item">
            <strong>Total réglé</strong>
            <strong>{resultat.total.toFixed(2)}€</strong>
          </div>
          <div className="liste-item">
            <span className="muted">Nouveau solde</span>
            <span className="badge badge-accent">{resultat.nouveau_solde.toFixed(2)}€</span>
          </div>
        </div>

        {resultat.lignes.some((l) => l.tickets_codes?.length) && (
          <div className="liste" style={{ textAlign: "left" }}>
            {resultat.lignes.flatMap((l) =>
              (l.tickets_codes || []).map((code, i) => (
                <div className="liste-item" key={`${code}-${i}`}>
                  <div>
                    <div className="muted" style={{ fontSize: 12.5 }}>{l.nom} — code de connexion</div>
                    <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: "0.15em" }}>{code}</div>
                  </div>
                  <button className="icon-btn" title="Copier le code" onClick={() => copierCode(code)}>
                    <Copy size={16} />
                  </button>
                </div>
              ))
            )}
            {codeCopie && <p className="muted" style={{ fontSize: 12.5, textAlign: "center" }}>Copié !</p>}
          </div>
        )}

        <p className="muted" style={{ fontSize: 13 }}>
          {resultat.lignes.some((l) => l.tickets_codes?.length)
            ? "Vos forfaits sont prêts à l'emploi depuis l'accueil — vous pourrez choisir lequel utiliser pour vous connecter."
            : "Vos commandes d'articles sont suivies jusqu'à la récupération à l'accueil."}
          {" "}Les reçus (tickets de caisse) restent téléchargeables depuis l'onglet Suivi.
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-block" onClick={() => navigate("/consommation")}>Voir mes reçus</button>
          <button className="btn btn-primary btn-block" onClick={() => navigate("/")}>Accueil</button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="section-titre">
        <ShoppingCart size={17} /> Mon panier
      </div>

      {items.length === 0 ? (
        <div className="card empty-state">
          Votre panier est vide.
          <div style={{ marginTop: 12 }}>
            <Link className="btn btn-primary" to="/boutique">Parcourir la boutique</Link>
          </div>
        </div>
      ) : (
        <>
          <div className="card liste fade-in">
            {items.map((i) => (
              <div className="liste-item" key={`${i.type}-${i.id}`}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 22 }}>{i.type === "forfait" ? "📶" : i.emoji || "📦"}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{i.nom}</div>
                    <span className="muted" style={{ fontSize: 12.5 }}>
                      {i.type === "forfait" ? "Forfait" : "Article"} · {i.prix.toFixed(2)}€ l'unité
                    </span>
                  </div>
                </div>
                <div className="qty">
                  <button onClick={() => changerQuantite(i.type, i.id, i.quantite - 1)}><Minus size={13} /></button>
                  <span>{i.quantite}</span>
                  <button onClick={() => changerQuantite(i.type, i.id, i.quantite + 1)}><Plus size={13} /></button>
                </div>
                <strong style={{ minWidth: 60, textAlign: "right" }}>{(i.prix * i.quantite).toFixed(2)}€</strong>
                <button className="icon-btn" onClick={() => retirer(i.type, i.id)} title="Retirer">
                  <Trash2 size={16} style={{ color: "var(--danger)" }} />
                </button>
              </div>
            ))}
          </div>

          {error && <p className="error fade-in">{error}</p>}

          <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="liste-item" style={{ borderBottom: "none", padding: 0 }}>
              <span className="muted">Total du panier</span>
              <strong style={{ fontSize: 20 }}>{total.toFixed(2)}€</strong>
            </div>
            <div className="liste-item" style={{ borderBottom: "none", padding: 0 }}>
              <span className="muted">Mon solde</span>
              <span className={`badge ${soldeInsuffisant ? "badge-danger" : "badge-success"}`}>
                {profil?.solde_euros.toFixed(2)}€
              </span>
            </div>
            {soldeInsuffisant && (
              <Link className="btn btn-block" to="/recharge">
                <Wallet size={15} /> Solde insuffisant — recharger mon compte
              </Link>
            )}
            <button className="btn btn-primary btn-lg btn-block" onClick={commander} disabled={busy || soldeInsuffisant}>
              {busy ? "Commande en cours..." : `Commander (${total.toFixed(2)}€)`}
            </button>
          </div>
        </>
      )}
    </>
  );
}
