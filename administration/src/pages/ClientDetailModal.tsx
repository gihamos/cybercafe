import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { PlusCircle, X } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { AbonnementEntry, ClientUser, LimiteEffective, Offre, Paiement, SessionEntry, TicketEntry, VenteArticle } from "../api/types";

export default function ClientDetailModal({ client, onClose }: { client: ClientUser; onClose: () => void }) {
  const [abonnements, setAbonnements] = useState<AbonnementEntry[]>([]);
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [ventes, setVentes] = useState<VenteArticle[]>([]);
  const [paiements, setPaiements] = useState<Paiement[]>([]);
  const [tickets, setTickets] = useState<TicketEntry[]>([]);
  const [offres, setOffres] = useState<Offre[]>([]);
  const [limiteBP, setLimiteBP] = useState<LimiteEffective | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renforcerTarget, setRenforcerTarget] = useState<TicketEntry | null>(null);

  const chargerTickets = useCallback(() => {
    api.get<TicketEntry[]>(`/tickets/user/${client.id}`).then(setTickets).catch(() => {});
  }, [client.id]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<AbonnementEntry[]>(`/abonnement/user/${client.id}`),
      api.get<SessionEntry[]>(`/session/user/${client.id}`),
      api.get<VenteArticle[]>(`/article/ventes/liste?user_id=${client.id}`),
      api.get<Paiement[]>(`/paiement/?user_id=${client.id}`),
      api.get<Offre[]>("/offre/"),
      api.get<LimiteEffective>(`/bande-passante/effectif/${client.id}`),
    ])
      .then(([a, s, v, p, o, bp]) => {
        setAbonnements(a);
        setSessions([...s].sort((x, y) => new Date(y.date_debut).getTime() - new Date(x.date_debut).getTime()));
        setVentes(v);
        setPaiements(p);
        setOffres(o);
        setLimiteBP(bp);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"))
      .finally(() => setLoading(false));
    chargerTickets();
  }, [client.id, chargerTickets]);

  async function toggleTicketActif(t: TicketEntry) {
    try {
      const updated = await api.patch<TicketEntry>(`/tickets/${t.code}/${t.est_actif ? "desactiver" : "reactiver"}`);
      setTickets((prev) => prev.map((x) => (x.code === t.code ? updated : x)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

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
            {client.groupe_noms && client.groupe_noms.length > 0 && (
              <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
                {client.groupe_noms.map((nom) => (
                  <span key={nom} className="badge badge-accent">
                    {nom}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {limiteBP && (limiteBP.download_mbps != null || limiteBP.upload_mbps != null) && (
          <p className="muted" style={{ marginTop: 8 }}>
            Bande passante effective : {limiteBP.download_mbps ?? "—"} / {limiteBP.upload_mbps ?? "—"} Mbps
            {limiteBP.source === "groupe" ? " (héritée des groupes)" : " (spécifique au compte)"}
          </p>
        )}

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

            <Section titre="Tickets actifs">
              {tickets.length === 0 ? (
                <p className="muted">Aucun ticket rattaché à ce compte</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Nature</th>
                      <th>Accès</th>
                      <th>Restant</th>
                      <th>Statut</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {tickets.map((t) => (
                      <tr key={t.id}>
                        <td>
                          <code>{t.code}</code>
                        </td>
                        <td className="muted">
                          {t.type_ticket === "credit" ? `Bon ${t.credit_euros?.toFixed(2)}€` : t.offre_nom || "—"}
                        </td>
                        <td className="muted">
                          {t.type_ticket === "credit" ? "—" : t.acces === "poste" ? "Poste fixe" : t.acces === "wifi" ? "WiFi" : "Poste + WiFi"}
                        </td>
                        <td className="muted">
                          {t.restant_minutes != null ? `${t.restant_minutes} min` : ""}
                          {t.restant_data_mo != null ? ` ${t.restant_data_mo} Mo` : ""}
                          {t.restant_minutes == null && t.restant_data_mo == null && "—"}
                        </td>
                        <td>
                          <span className={`badge ${t.est_consomme ? "badge-neutral" : t.est_actif ? "badge-success" : "badge-danger"}`}>
                            {t.est_consomme ? "Utilisé" : t.est_actif ? "Actif" : "Désactivé"}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                            {!t.est_consomme && t.type_ticket !== "credit" && (
                              <button className="btn btn-sm" onClick={() => setRenforcerTarget(t)}>
                                <PlusCircle size={13} /> Renforcer
                              </button>
                            )}
                            {!t.est_consomme && (
                              <button className="btn btn-sm" onClick={() => toggleTicketActif(t)}>
                                {t.est_actif ? "Désactiver" : "Réactiver"}
                              </button>
                            )}
                          </div>
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

      {renforcerTarget && (
        <RenforcerTicketModal
          ticket={renforcerTarget}
          onClose={() => setRenforcerTarget(null)}
          onDone={(updated) => {
            setTickets((prev) => prev.map((x) => (x.code === updated.code ? updated : x)));
            setRenforcerTarget(null);
          }}
        />
      )}
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

function RenforcerTicketModal({
  ticket,
  onClose,
  onDone,
}: {
  ticket: TicketEntry;
  onClose: () => void;
  onDone: (t: TicketEntry) => void;
}) {
  const [minutes, setMinutes] = useState("30");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const updated = await api.post<TicketEntry>(`/tickets/${ticket.code}/renforcer?minutes=${minutes}`);
      onDone(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Renforcer le ticket {ticket.code}</h2>
        <p className="muted">Temps restant actuel : {ticket.restant_minutes ?? 0} min</p>
        {error && <p className="error">{error}</p>}
        <label>
          Minutes à ajouter
          <input type="number" min="1" value={minutes} onChange={(e) => setMinutes(e.target.value)} required autoFocus />
        </label>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Enregistrement..." : "Ajouter"}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
