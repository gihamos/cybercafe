import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Printer, Plus } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { FichierStocke, MonImpression } from "../api/types";

const STATUT_BADGE: Record<string, string> = {
  en_attente: "badge-warning",
  en_cours: "badge-accent",
  succes: "badge-success",
  echec: "badge-danger",
  annulee: "badge",
};

export default function ImpressionsPage() {
  const [impressions, setImpressions] = useState<MonImpression[]>([]);
  const [fichiers, setFichiers] = useState<FichierStocke[]>([]);
  const [tarifs, setTarifs] = useState<{ prix_nb: number; prix_couleur: number } | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [fichierId, setFichierId] = useState("");
  const [pages, setPages] = useState("1");
  const [couleur, setCouleur] = useState(false);
  const [rectoVerso, setRectoVerso] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const charger = useCallback(async () => {
    api.get<MonImpression[]>("/portail/impressions").then(setImpressions).catch(() => {});
    api.get<FichierStocke[]>("/stockage/fichiers").then(setFichiers).catch(() => {});
    api.get<{ prix_nb: number; prix_couleur: number }>("/portail/impression/tarifs").then(setTarifs).catch(() => {});
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  const prixParPage = tarifs ? (couleur ? tarifs.prix_couleur : tarifs.prix_nb) : null;
  const prixEstime = prixParPage != null ? prixParPage * (parseInt(pages, 10) || 0) : null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setSaving(true);
    try {
      await api.post("/portail/impressions", {
        fichier_id: parseInt(fichierId, 10),
        pages: parseInt(pages, 10),
        type_impression: couleur ? "couleur" : "noir_blanc",
        recto_verso: rectoVerso,
      });
      setMessage("Demande envoyée ! Présentez-vous à l'accueil pour le règlement et la récupération.");
      setShowForm(false);
      setFichierId("");
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
          <Printer size={17} /> Mes impressions
        </span>
        <button className="btn btn-sm btn-primary" onClick={() => setShowForm((v) => !v)}>
          <Plus size={14} /> Nouvelle demande
        </button>
      </div>

      {message && <p className="success-box fade-in">{message}</p>}

      {showForm && (
        <form className="card fade-in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <p className="error">{error}</p>}
          {fichiers.length === 0 ? (
            <p className="muted" style={{ fontSize: 14 }}>
              Envoyez d'abord votre document dans « Fichiers », puis revenez ici pour demander son impression.
            </p>
          ) : (
            <>
              <label>
                Document à imprimer
                <select value={fichierId} onChange={(e) => setFichierId(e.target.value)} required>
                  <option value="">Choisir un fichier...</option>
                  {fichiers.map((f) => (
                    <option key={f.id} value={f.id}>{f.nom_original}</option>
                  ))}
                </select>
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
              {prixEstime != null && (
                <div className="liste-item" style={{ borderBottom: "none", padding: 0 }}>
                  <span className="muted">Prix estimé ({prixParPage?.toFixed(2)}€/page)</span>
                  <strong>{prixEstime.toFixed(2)}€</strong>
                </div>
              )}
              <button className="btn btn-primary btn-block" type="submit" disabled={saving || !fichierId}>
                <Printer size={15} /> {saving ? "Envoi..." : "Demander l'impression"}
              </button>
            </>
          )}
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
