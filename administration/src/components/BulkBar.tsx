import { useState } from "react";
import type { ReactNode } from "react";

/** Sélection multiple générique pour les tableaux (clients, tickets, offres...). */
export function useSelection<K extends string | number>() {
  const [selected, setSelected] = useState<Set<K>>(new Set());

  function toggle(key: K) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  /** Coche tout si la sélection est incomplète, décoche tout sinon. */
  function toggleAll(keys: K[]) {
    setSelected((prev) => (keys.every((k) => prev.has(k)) && keys.length > 0 ? new Set() : new Set(keys)));
  }

  function clear() {
    setSelected(new Set<K>());
  }

  return { selected, toggle, toggleAll, clear };
}

/**
 * Applique une action à chaque élément sélectionné (en réutilisant les endpoints
 * unitaires existants, donc les mêmes contrôles de permissions côté serveur),
 * puis résume les succès/échecs.
 */
export async function executerActionGroupee<T>(
  items: T[],
  action: (item: T) => Promise<unknown>
): Promise<{ ok: number; erreurs: string[] }> {
  const resultats = await Promise.allSettled(items.map((item) => action(item)));
  const erreurs = resultats
    .filter((r): r is PromiseRejectedResult => r.status === "rejected")
    .map((r) => (r.reason instanceof Error ? r.reason.message : String(r.reason)));
  return { ok: resultats.length - erreurs.length, erreurs };
}

export function resumeActionGroupee(libelle: string, resultat: { ok: number; erreurs: string[] }): string {
  if (resultat.erreurs.length === 0) return `${libelle} : ${resultat.ok} élément(s) traité(s).`;
  const detail = [...new Set(resultat.erreurs)].slice(0, 3).join(" / ");
  return `${libelle} : ${resultat.ok} réussi(s), ${resultat.erreurs.length} échec(s) — ${detail}`;
}

/** Barre d'actions groupées affichée quand au moins un élément est coché. */
export function BulkBar({
  count,
  onClear,
  children,
}: {
  count: number;
  onClear: () => void;
  children: ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div
      className="card"
      style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", padding: "10px 14px" }}
    >
      <strong>{count} sélectionné(s)</strong>
      {children}
      <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={onClear}>
        Tout désélectionner
      </button>
    </div>
  );
}
