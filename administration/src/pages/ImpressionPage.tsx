import { useCallback, useEffect, useState } from "react";
import { Download, Printer } from "lucide-react";
import { api, ApiError, downloadFile } from "../api/client";
import type { Impression, StatutImpression, SystemSetting } from "../api/types";

const STATUT_BADGE: Record<StatutImpression, string> = {
  en_attente: "badge-warning",
  en_cours: "badge-warning",
  succes: "badge-success",
  echec: "badge-danger",
  annulee: "badge-neutral",
};

const TARIF_KEYS = [
  { cle: "impression.prix_nb", label: "Prix par page (noir & blanc)", defaut: 0.1 },
  { cle: "impression.prix_couleur", label: "Prix par page (couleur)", defaut: 0.25 },
];

export default function ImpressionPage() {
  const [settings, setSettings] = useState<Record<string, SystemSetting>>({});
  const [impressions, setImpressions] = useState<Impression[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [settingsData, impressionsData] = await Promise.all([
        api.get<SystemSetting[]>("/system-setting/categorie/impression"),
        api.get<Impression[]>("/impression/"),
      ]);
      const byKey: Record<string, SystemSetting> = {};
      settingsData.forEach((s) => { byKey[s.cle] = s; });
      setSettings(byKey);
      setImpressions(impressionsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function action(i: Impression, chemin: string, confirmation?: string) {
    if (confirmation && !confirm(confirmation)) return;
    try {
      const updated = await api.post<Impression>(`/impression/${i.id}/${chemin}`);
      setImpressions((prev) => prev.map((x) => (x.id === i.id ? updated : x)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function payer(i: Impression) {
    const solde = i.user_id != null && confirm(
      `Encaisser ${i.prix_total.toFixed(2)}€ — OK pour débiter le solde du client, Annuler pour un paiement en espèces.`
    );
    try {
      const params = solde ? "utiliser_solde=true" : "type_paiement=especes";
      const updated = await api.post<Impression>(`/impression/${i.id}/payer?${params}`);
      setImpressions((prev) => prev.map((x) => (x.id === i.id ? updated : x)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  async function telechargerDocument(i: Impression) {
    try {
      await downloadFile(`/impression/${i.id}/document`, i.fichier_nom);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Document indisponible");
    }
  }

  async function saveTarif(cle: string, valeur: number) {
    try {
      const existing = settings[cle];
      if (existing) {
        const updated = await api.patch<SystemSetting>(`/system-setting/${cle}`, { valeur });
        setSettings((prev) => ({ ...prev, [cle]: updated }));
      } else {
        const created = await api.post<SystemSetting>("/system-setting/", {
          cle,
          categorie: "impression",
          valeur,
        });
        setSettings((prev) => ({ ...prev, [cle]: created }));
      }
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <h1>
          <Printer size={20} /> Impression
        </h1>
      {error && <p className="error">{error}</p>}

      <div className="card">
        <h2>Tarifs</h2>
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 360 }}>
            {TARIF_KEYS.map(({ cle, label, defaut }) => (
              <TarifInput
                key={cle}
                label={label}
                valeurInitiale={(settings[cle]?.valeur as number) ?? defaut}
                onSave={(v) => saveTarif(cle, v)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2>Historique des impressions</h2>
        {loading ? (
          <p className="muted">Chargement...</p>
        ) : impressions.length === 0 ? (
          <div className="empty-state">Aucune impression</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Fichier</th>
                <th>Pages</th>
                <th>Type</th>
                <th>Prix</th>
                <th>Règlement</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {impressions.map((i) => (
                <tr key={i.id}>
                  <td className="muted">{new Date(i.date_impression).toLocaleString()}</td>
                  <td>{i.fichier_nom}</td>
                  <td>
                    {i.pages_total} {i.recto_verso ? "(R/V)" : ""}
                  </td>
                  <td className="muted">{i.type_impression === "couleur" ? "Couleur" : "N&B"}</td>
                  <td>{i.prix_total.toFixed(2)}€</td>
                  <td>
                    <span className={`badge ${i.paye ? "badge-success" : "badge-warning"}`}>
                      {i.paye ? "Réglée" : "À encaisser"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${STATUT_BADGE[i.statut]}`}>{i.statut}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", flexWrap: "wrap" }}>
                      {i.document_disponible && (
                        <button className="btn btn-sm" onClick={() => telechargerDocument(i)} title="Télécharger le document à imprimer">
                          <Download size={13} />
                        </button>
                      )}
                      {!i.paye && i.statut === "en_attente" && (
                        <button className="btn btn-sm" onClick={() => payer(i)}>
                          Encaisser
                        </button>
                      )}
                      {i.paye && i.statut === "en_attente" && (
                        <button className="btn btn-sm btn-primary" onClick={() => action(i, "demarrer")}>
                          Lancer
                        </button>
                      )}
                      {i.statut === "en_cours" && (
                        <button className="btn btn-sm btn-primary" onClick={() => action(i, "terminer")}>
                          Terminée
                        </button>
                      )}
                      {i.statut === "en_cours" && (
                        <button className="btn btn-sm btn-danger" onClick={() => action(i, "erreur?message=Echec%20imprimante")}>
                          Échec
                        </button>
                      )}
                      {i.statut === "en_attente" && (
                        <button className="btn btn-sm btn-danger" onClick={() => action(i, "annuler", "Annuler cette impression ?")}>
                          Annuler
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function TarifInput({
  label,
  valeurInitiale,
  onSave,
}: {
  label: string;
  valeurInitiale: number;
  onSave: (v: number) => void;
}) {
  const [valeur, setValeur] = useState(String(valeurInitiale));
  const [saved, setSaved] = useState(false);

  return (
    <label>
      {label} (€)
      <div style={{ display: "flex", gap: 6 }}>
        <input
          type="number"
          step="0.01"
          min="0"
          value={valeur}
          onChange={(e) => {
            setValeur(e.target.value);
            setSaved(false);
          }}
        />
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => {
            onSave(parseFloat(valeur));
            setSaved(true);
          }}
        >
          {saved ? "Enregistré ✓" : "Enregistrer"}
        </button>
      </div>
    </label>
  );
}
