import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Printer, Plus } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { MonImpression } from "../api/types";

const STATUT_BADGE: Record<string, string> = {
  en_attente: "badge-warning",
  en_cours: "badge-accent",
  succes: "badge-success",
  echec: "badge-danger",
  annulee: "badge",
};

/** Impression en mode ticket : pas d'espace fichiers persistant ni de solde — le
 * fichier est envoyé directement avec la demande, réglée en espèces à l'accueil. */
export default function TicketImpressionPage() {
  const [impressions, setImpressions] = useState<MonImpression[]>([]);
  const [showForm, setShowForm] = useState(false);

  const [fichier, setFichier] = useState<File | null>(null);
  const [pages, setPages] = useState("1");
  const [couleur, setCouleur] = useState(false);
  const [rectoVerso, setRectoVerso] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const charger = useCallback(async () => {
    api.get<MonImpression[]>("/portail/ticket/impressions").then(setImpressions).catch(() => {});
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!fichier) return;
    setError(null);
    setMessage(null);
    setSaving(true);
    try {
      await api.upload("/portail/ticket/impressions", fichier, {
        pages,
        type_impression: couleur ? "couleur" : "noir_blanc",
        recto_verso: String(rectoVerso),
      });
      setMessage("Demande envoyée ! Présentez-vous à l'accueil pour le règlement et la récupération.");
      setShowForm(false);
      setFichier(null);
      setPages("1");
      await charger();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la demande");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="section-titre" style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Printer size={17} /> Imprimer un document
        </span>
        <button className="btn btn-sm btn-primary" onClick={() => setShowForm((v) => !v)}>
          <Plus size={14} /> Nouvelle demande
        </button>
      </div>

      {message && <p className="success-box fade-in">{message}</p>}

      {showForm && (
        <form className="card fade-in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <p className="error">{error}</p>}
          <label>
            Document à imprimer
            <input
              type="file"
              onChange={(e) => setFichier(e.target.files?.[0] || null)}
              required
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label>
              Nombre de pages
              <input type="number" min="1" max="500" value={pages} onChange={(e) => setPages(e.target.value)} required />
            </label>
            <label>
              Options
              <div style={{ display: "flex", flexDirection: "column", gap: 6, fontWeight: 400 }}>
                <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={couleur} onChange={(e) => setCouleur(e.target.checked)} style={{ width: "auto" }} />
                  Couleur
                </label>
                <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={rectoVerso} onChange={(e) => setRectoVerso(e.target.checked)} style={{ width: "auto" }} />
                  Recto-verso
                </label>
              </div>
            </label>
          </div>
          <p className="muted" style={{ fontSize: 12.5 }}>
            Réglement en espèces à l'accueil au moment de la récupération.
          </p>
          <button className="btn btn-primary btn-block" type="submit" disabled={saving || !fichier}>
            <Printer size={15} /> {saving ? "Envoi..." : "Demander l'impression"}
          </button>
        </form>
      )}

      <div className="card">
        {impressions.length === 0 ? (
          <div className="empty-state">Aucune impression demandée</div>
        ) : (
          <div className="liste">
            {impressions.map((i) => (
              <div className="liste-item" key={i.id}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {i.fichier_nom}
                  </div>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {i.pages_total} page(s) · {i.type_impression === "couleur" ? "Couleur" : "N&B"}
                    {i.recto_verso ? " · R/V" : ""} · {new Date(i.date_impression).toLocaleDateString()}
                  </span>
                </div>
                <div style={{ textAlign: "right", display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
                  <span className={`badge ${STATUT_BADGE[i.statut] || ""}`}>{i.statut}</span>
                  {i.prix_total != null && <strong style={{ fontSize: 13.5 }}>{i.prix_total.toFixed(2)}€</strong>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
