import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { AbonnementEntry, ClientUser, Offre, Paiement, SessionEntry, VenteArticle } from "../api/types";

export default function ClientDetailModal({ client, onClose }: { client: ClientUser; onClose: () => void }) {
  const [abonnements, setAbonnements] = useState<AbonnementEntry[]>([]);
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [ventes, setVentes] = useState<VenteArticle[]>([]);
  const [paiements, setPaiements] = useState<Paiement[]>([]);
  const [offres, setOffres] = useState<Offre[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<AbonnementEntry[]>(`/abonnement/user/${client.id}`),
      api.get<SessionEntry[]>(`/session/user/${client.id}`),
      api.get<VenteArticle[]>(`/article/ventes/liste?user_id=${client.id}`),
      api.get<Paiement[]>(`/paiement/?user_id=${client.id}`),
      api.get<Offre[]>("/offre/"),
    ])
      .then(([a, s, v, p, o]) => {
        setAbonnements(a);
        setSessions([...s].sort((x, y) => new Date(y.date_debut).getTime() - new Date(x.date_debut).getTime()));
        setVentes(v);
        setPaiements(p);
        setOffres(o);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, [client.id]);

  const offreNom = (id: number) => offres.find((o) => o.id === id)?.nom || `Offre #${id}`;
  const derniereSession = sessions[0];
  const forfaitsActifs = abonnements.filter((a) => a.est_actif && !a.est_suspendu);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} style={{ width: 620, maxHeight: "85vh", overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>{client.username}</h2>
            <p className="muted">{client.email}</p>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="stat-tiles" style={{ marginTop: 12 }}>
          <div className="stat-tile">
            <span className="stat-tile-label">Solde</span>
            <span className="stat-tile-value">{client.solde_euros.toFixed(2)}€</span>
          </div>
          <div className="stat-tile">
            <span className="stat-tile-label">Forfaits actifs</span>
            <span className="stat-tile-value">{forfaitsActifs.length}</span>
          </div>
          <div className="stat-tile">
            <span className="stat-tile-label">Dernière connexion</span>
            <span className="stat-tile-value" style={{ fontSize: 15 }}>
              {derniereSession ? new Date(derniereSession.date_debut).toLocaleDateString() : "Jamais"}
            </span>
            {derniereSession && (
              <span className="stat-tile-sub">
                {derniereSession.est_active ? "En cours" : new Date(derniereSession.date_debut).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {error && <p className="error">{error}</p>}
        {loading ? (
          <p className="muted" style={{ marginTop: 12 }}>
            Chargement...
          </p>
        ) : (
          <>
            <Section titre="Forfaits & abonnements">
              {abonnements.length === 0 ? (
                <p className="muted">Aucun abonnement souscrit</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Offre</th>
                      <th>Début</th>
                      <th>Fin</th>
                      <th>Restant</th>
                      <th>Statut</th>
                    </tr>
                  </thead>
                  <tbody>
                    {abonnements.map((a) => (
                      <tr key={a.id}>
                        <td>{offreNom(a.offre_id)}</td>
                        <td className="muted">{new Date(a.date_debut).toLocaleDateString()}</td>
                        <td className="muted">{a.date_fin ? new Date(a.date_fin).toLocaleDateString() : "—"}</td>
                        <td className="muted">
                          {a.illimite
                            ? "Illimité"
                            : a.minutes_restantes_aujourdhui != null
                              ? `${a.minutes_restantes_aujourdhui} min`
                              : a.data_restante_mo != null
                                ? `${a.data_restante_mo} Mo`
                                : "—"}
                        </td>
                        <td>
                          <span className={`badge ${!a.est_actif ? "badge-neutral" : a.est_suspendu ? "badge-warning" : "badge-success"}`}>
                            {!a.est_actif ? "Expiré" : a.est_suspendu ? "Suspendu" : "Actif"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>

            <Section titre="Sessions récentes">
              {sessions.length === 0 ? (
                <p className="muted">Aucune session enregistrée</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Poste</th>
                      <th>Début</th>
                      <th>Consommation</th>
                      <th>Statut</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.slice(0, 10).map((s) => (
                      <tr key={s.id}>
                        <td>#{s.poste_id}</td>
                        <td className="muted">{new Date(s.date_debut).toLocaleString()}</td>
                        <td className="muted">
                          {s.consommation_minutes} min{s.consommation_data_mo ? ` / ${s.consommation_data_mo.toFixed(0)} Mo` : ""}
                        </td>
                        <td>
                          <span className={`badge ${s.est_active ? "badge-success" : "badge-neutral"}`}>
                            {s.est_active ? "En cours" : "Terminée"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>

            <Section titre="Achats d'articles">
              {ventes.length === 0 ? (
                <p className="muted">Aucun achat</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Article</th>
                      <th>Prix</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ventes.slice(0, 10).map((v) => (
                      <tr key={v.id}>
                        <td>{v.article_nom}</td>
                        <td>{v.prix.toFixed(2)}€</td>
                        <td className="muted">{new Date(v.date_achat).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>

            <Section titre="Paiements">
              {paiements.length === 0 ? (
                <p className="muted">Aucun paiement</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Montant</th>
                      <th>Moyen</th>
                      <th>Statut</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paiements.slice(0, 10).map((p) => (
                      <tr key={p.id}>
                        <td>{p.montant.toFixed(2)}€</td>
                        <td className="muted">{p.type_paiement}</td>
                        <td>
                          <span className={`badge ${p.statut === "succes" ? "badge-success" : p.statut === "en_attente" ? "badge-warning" : "badge-neutral"}`}>
                            {p.statut}
                          </span>
                        </td>
                        <td className="muted">{new Date(p.date_paiement).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>
          </>
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

function Section({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <div style={{ marginTop: 20 }}>
      <h3>{titre}</h3>
      <div style={{ marginTop: 8 }}>{children}</div>
    </div>
  );
}
