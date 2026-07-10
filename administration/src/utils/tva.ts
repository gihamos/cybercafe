/** Les prix des offres/articles sont saisis TTC — ce calcul n'en déduit que la
 * décomposition HT/TVA pour affichage (reçus, tickets), il ne change jamais le
 * montant réellement facturé. */
export function decomposerTTC(montantTTC: number, tauxTvaPourcent: number): { montantHT: number; montantTva: number } {
  const montantHT = montantTTC / (1 + tauxTvaPourcent / 100);
  return { montantHT, montantTva: montantTTC - montantHT };
}
