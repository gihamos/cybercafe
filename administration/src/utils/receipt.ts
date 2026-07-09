export interface ReceiptLine {
  label: string;
  value: string;
}

/** Ouvre un reçu imprimable dans un nouvel onglet et déclenche l'impression —
 * utilisé pour les ventes d'articles, les paiements et les recharges de solde.
 * Une fenêtre séparée (plutôt qu'une feuille de style @media print sur le SPA)
 * garde l'impression simple et fiable quel que soit l'état de la page courante. */
export function printReceipt(opts: {
  titre: string;
  sousTitre?: string;
  lignes: ReceiptLine[];
  total?: string;
  pied?: string;
}) {
  const win = window.open("", "_blank", "width=380,height=600");
  if (!win) return;

  const lignesHtml = opts.lignes
    .map((l) => `<div class="row"><span>${escapeHtml(l.label)}</span><span>${escapeHtml(l.value)}</span></div>`)
    .join("");

  win.document.write(`<!doctype html>
<html>
<head>
<title>Reçu</title>
<meta charset="utf-8" />
<style>
  * { box-sizing: border-box; }
  body { font-family: "Courier New", monospace; font-size: 13px; padding: 20px; color: #111; max-width: 340px; margin: 0 auto; }
  h1 { font-size: 16px; text-align: center; margin: 0 0 2px; letter-spacing: 0.02em; }
  .sub { text-align: center; color: #555; margin-bottom: 18px; font-size: 12px; }
  .row { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dashed #ccc; }
  .total { display: flex; justify-content: space-between; font-weight: bold; margin-top: 12px; padding-top: 10px; border-top: 2px solid #111; font-size: 15px; }
  .footer { text-align: center; margin-top: 24px; font-size: 11px; color: #666; white-space: pre-line; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
  <h1>${escapeHtml(opts.titre)}</h1>
  ${opts.sousTitre ? `<div class="sub">${escapeHtml(opts.sousTitre)}</div>` : ""}
  ${lignesHtml}
  ${opts.total ? `<div class="total"><span>Total</span><span>${escapeHtml(opts.total)}</span></div>` : ""}
  ${opts.pied ? `<div class="footer">${escapeHtml(opts.pied)}</div>` : ""}
</body>
</html>`);
  win.document.close();
  win.focus();
  win.print();
}

function escapeHtml(value: string): string {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}
