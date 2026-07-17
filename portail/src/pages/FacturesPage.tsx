import { useEffect, useState } from "react";
import { Download, Package, Receipt, ShoppingBag, Wallet } from "lucide-react";
import { api, downloadFile } from "../api/client";
import type { MonPaiement } from "../api/types";

const STATUT_BADGE: Record<string, string> = {
  succes: "badge-success",
  en_attente: "badge-warning",
  echec: "badge-danger",
  annule: "badge",
};

const NATURE_ICON: Record<MonPaiement["nature"], typeof Package> = {
  forfait: Package,
  article: ShoppingBag,
  credit: Wallet,
};

const NATURE_LABEL: Record<MonPaiement["nature"], string> = {
  forfait: "Forfait",
  article: "Article",
  credit: "Recharge",
};

export default function FacturesPage() {
  const [paiements, setPaiements] = useState<MonPaiement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<MonPaiement[]>("/portail/paiements").then(setPaiements).finally(() => setLoading(false));
  }, []);

  function telechargerRecu(paiementId: number) {
    downloadFile(`/portail/paiements/${paiementId}/recu`, `recu-${paiementId}.html`).catch(() => {
      alert("Reçu indisponible");
    });
  }

  return (
    <>
      <div className="section-titre">
        <Receipt size={17} /> Tickets & factures
      </div>
      <p className="muted" style={{ fontSize: 13, marginTop: -8 }}>
        Tous vos règlements — forfaits, articles, recharges de solde — avec le reçu téléchargeable de chacun.
      </p>

      <div className="card">
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : paiements.length === 0 ? (
          <div className="empty-state">Aucun règlement pour le moment</div>
        ) : (
          <div className="liste">
            {paiements.map((p) => {
              const Icone = NATURE_ICON[p.nature] || Receipt;
              return (
                <div className="liste-item" key={p.id}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                    <Icone size={18} style={{ flexShrink: 0, color: "var(--accent)" }} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {p.libelle}
                      </div>
                      <span className="muted" style={{ fontSize: 12.5 }}>
                        {NATURE_LABEL[p.nature]} · {new Date(p.date_paiement).toLocaleString()} · {p.type_paiement}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <strong>{p.montant.toFixed(2)}€</strong>
                    <span className={`badge ${STATUT_BADGE[p.statut] || ""}`}>{p.statut}</span>
                    {p.statut === "succes" && (
                      <button className="icon-btn" title="Télécharger le reçu" onClick={() => telechargerRecu(p.id)}>
                        <Download size={16} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
