import { useEffect, useState } from "react";
import { BarChart3, CreditCard, Download, Package, ShoppingBag } from "lucide-react";
import { api, downloadFile } from "../api/client";
import type { AbonnementCourant, MaConsommation, MesAchats, MonPaiement } from "../api/types";

const STATUT_BADGE: Record<string, string> = {
  succes: "badge-success",
  en_attente: "badge-warning",
  echec: "badge-danger",
  annule: "badge",
};

const STATUT_COMMANDE: Record<string, { label: string; cls: string }> = {
  a_preparer: { label: "En préparation", cls: "badge-warning" },
  prete: { label: "Prête — à récupérer à l'accueil", cls: "badge-accent" },
  recuperee: { label: "Récupérée", cls: "badge-success" },
};

export default function ConsommationPage() {
  const [conso, setConso] = useState<MaConsommation | null>(null);
  const [paiements, setPaiements] = useState<MonPaiement[]>([]);
  const [forfaits, setForfaits] = useState<AbonnementCourant[]>([]);
  const [achats, setAchats] = useState<MesAchats | null>(null);

  useEffect(() => {
    api.get<MaConsommation>("/portail/consommation").then(setConso).catch(() => {});
    api.get<MonPaiement[]>("/portail/paiements").then(setPaiements).catch(() => {});
    api.get<AbonnementCourant[]>("/portail/mes-forfaits").then(setForfaits).catch(() => {});
    api.get<MesAchats>("/portail/achats").then(setAchats).catch(() => {});
  }, []);

  function telechargerRecu(paiementId: number) {
    downloadFile(`/portail/paiements/${paiementId}/recu`, `recu-${paiementId}.html`).catch(() => {
      alert("Reçu indisponible");
    });
  }

  return (
    <>
      <div className="section-titre">
        <BarChart3 size={17} /> Suivi de consommation
      </div>

      <div className="stat-grid">
        <div className="card stat-tile">
          <span className="label">Temps total</span>
          <span className="valeur">
            {conso ? `${Math.floor(conso.total_minutes / 60)}h ${conso.total_minutes % 60}m` : "—"}
          </span>
        </div>
        <div className="card stat-tile">
          <span className="label">Données</span>
          <span className="valeur">{conso ? `${conso.total_data_mo.toFixed(0)} Mo` : "—"}</span>
        </div>
        <div className="card stat-tile">
          <span className="label">Sessions</span>
          <span className="valeur">{conso?.sessions.length ?? "—"}</span>
        </div>
      </div>

      <div className="card">
        <div className="section-titre">
          <Package size={15} /> Mes forfaits actifs
        </div>
        {forfaits.length === 0 ? (
          <div className="empty-state">Aucun forfait actif — retrouvez-les dans la boutique.</div>
        ) : (
          <div className="liste">
            {forfaits.map((f) => (
              <div className="liste-item" key={f.id}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{f.offre_nom || "Forfait"}</div>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {f.illimite
                      ? "Accès illimité"
                      : f.minutes_restantes_aujourdhui != null
                        ? `${f.minutes_restantes_aujourdhui} min restantes aujourd'hui`
                        : f.data_restante_mo != null
                          ? `${f.data_restante_mo.toFixed(0)} Mo restants`
                          : "Actif"}
                    {f.date_fin && ` · expire le ${new Date(f.date_fin).toLocaleDateString()}`}
                  </span>
                </div>
                <span className={`badge ${f.est_suspendu ? "badge-warning" : "badge-success"}`}>
                  {f.est_suspendu ? "Suspendu" : "Actif"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-titre">
          <ShoppingBag size={15} /> Mes achats & commandes
        </div>
        {!achats || (achats.articles.length === 0 && achats.forfaits.length === 0) ? (
          <div className="empty-state">Aucun achat pour le moment</div>
        ) : (
          <div className="liste">
            {achats.articles.map((a) => {
              const st = STATUT_COMMANDE[a.statut_commande] || STATUT_COMMANDE.recuperee;
              return (
                <div className="liste-item" key={`a-${a.id}`}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{a.article_nom || "Article"}</div>
                    <span className="muted" style={{ fontSize: 12.5 }}>
                      {new Date(a.date_achat).toLocaleString()} · {a.prix.toFixed(2)}€
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span className={`badge ${st.cls}`}>{st.label}</span>
                    {a.paiement_id != null && (
                      <button className="icon-btn" title="Télécharger le reçu" onClick={() => telechargerRecu(a.paiement_id!)}>
                        <Download size={16} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
            {achats.forfaits.map((f) => (
              <div className="liste-item" key={`f-${f.id}`}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{f.offre_nom || "Forfait"}</div>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {new Date(f.date_achat).toLocaleString()}
                    {f.prix != null && ` · ${f.prix.toFixed(2)}€`}
                  </span>
                </div>
                <span className="badge badge-accent">Forfait</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-titre">Historique des sessions</div>
        {!conso || conso.sessions.length === 0 ? (
          <div className="empty-state">Aucune session pour le moment</div>
        ) : (
          <div className="liste">
            {conso.sessions.map((s) => (
              <div className="liste-item" key={s.id}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>
                    {new Date(s.date_debut).toLocaleDateString()}{" "}
                    <span className="muted" style={{ fontWeight: 400 }}>
                      {new Date(s.date_debut).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <span className="muted" style={{ fontSize: 12.5 }}>{s.poste_nom || "WiFi"}</span>
                </div>
                <div style={{ textAlign: "right" }}>
                  {s.est_active ? (
                    <span className="badge badge-success">En cours</span>
                  ) : (
                    <strong>{s.consommation_minutes} min</strong>
                  )}
                  {s.consommation_data_mo > 0 && (
                    <div className="muted" style={{ fontSize: 12 }}>{s.consommation_data_mo.toFixed(0)} Mo</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-titre">
          <CreditCard size={15} /> Mes paiements
        </div>
        {paiements.length === 0 ? (
          <div className="empty-state">Aucun paiement</div>
        ) : (
          <div className="liste">
            {paiements.map((p) => (
              <div className="liste-item" key={p.id}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{p.montant.toFixed(2)}€</div>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {new Date(p.date_paiement).toLocaleDateString()} · {p.type_paiement}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span className={`badge ${STATUT_BADGE[p.statut] || ""}`}>{p.statut}</span>
                  {p.statut === "succes" && (
                    <button className="icon-btn" title="Télécharger le reçu (ticket de caisse)" onClick={() => telechargerRecu(p.id)}>
                      <Download size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
