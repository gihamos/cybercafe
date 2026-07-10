import { api } from "../api/client";
import type { CybercafeConfig } from "../api/types";

export interface ReceiptLine {
  label: string;
  value: string;
}

/** Récupère la configuration du cybercafé (nom, logo, adresse, téléphone, SIRET,
 * pied de reçu) pour l'imprimer sur les reçus et tickets — en échec (réseau,
 * config jamais définie...), on retombe sur un en-tête minimal plutôt que de
 * bloquer l'impression. */
async function fetchShopConfig(): Promise<Partial<CybercafeConfig>> {
  try {
    return await api.get<CybercafeConfig>("/config/cybercafe");
  } catch {
    return {};
  }
}

function shopHeaderHtml(config: Partial<CybercafeConfig>): string {
  const nom = config["cybercafe.nom"] || "Cybercafé";
  const logo = config["cybercafe.logo"];
  const adresse = config["cybercafe.adresse"];
  const telephone = config["cybercafe.telephone"];
  const siret = config["cybercafe.siret"];

  const coordonnees = [adresse, telephone ? `Tél. ${telephone}` : null, siret ? `SIRET ${siret}` : null]
    .filter(Boolean)
    .map((ligne) => `<div>${escapeHtml(ligne as string)}</div>`)
    .join("");

  return `
    ${logo ? `<img src="${logo}" alt="${escapeHtml(nom)}" class="logo" />` : ""}
    <h1>${escapeHtml(nom)}</h1>
    ${coordonnees ? `<div class="coordonnees">${coordonnees}</div>` : ""}
  `;
}

const SHARED_STYLE = `
  * { box-sizing: border-box; }
  .logo { display: block; max-width: 120px; max-height: 80px; margin: 0 auto 8px; object-fit: contain; }
  h1 { font-size: 16px; text-align: center; margin: 0 0 2px; letter-spacing: 0.02em; }
  .coordonnees { text-align: center; color: #555; font-size: 11px; line-height: 1.5; margin-bottom: 10px; }
`;

/** Ouvre un reçu imprimable dans un nouvel onglet et déclenche l'impression —
 * utilisé pour les ventes d'articles, les paiements et les recharges de solde.
 * Une fenêtre séparée (plutôt qu'une feuille de style @media print sur le SPA)
 * garde l'impression simple et fiable quel que soit l'état de la page courante.
 * L'en-tête (nom, logo, adresse, téléphone, SIRET) vient de la configuration du
 * cybercafé (Paramètres) — chaque champ absent est simplement omis, jamais affiché
 * vide. Le pied de page combine `reference` (propre à ce reçu, ex. son numéro) et
 * le pied de reçu configuré (ex. "Merci de votre visite !"), les deux étant
 * optionnels indépendamment. */
export async function printReceipt(opts: {
  sousTitre?: string;
  lignes: ReceiptLine[];
  total?: string;
  reference?: string;
}) {
  const win = window.open("", "_blank", "width=380,height=600");
  if (!win) return;

  const config = await fetchShopConfig();
  const pied = [opts.reference, config["cybercafe.pied_recu"]].filter(Boolean).join("\n");

  const lignesHtml = opts.lignes
    .map((l) => `<div class="row"><span>${escapeHtml(l.label)}</span><span>${escapeHtml(l.value)}</span></div>`)
    .join("");

  win.document.write(`<!doctype html>
<html>
<head>
<title>Reçu</title>
<meta charset="utf-8" />
<style>
  ${SHARED_STYLE}
  body { font-family: "Courier New", monospace; font-size: 13px; padding: 20px; color: #111; max-width: 340px; margin: 0 auto; }
  .sub { text-align: center; color: #555; margin-bottom: 18px; font-size: 12px; }
  .row { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dashed #ccc; }
  .total { display: flex; justify-content: space-between; font-weight: bold; margin-top: 12px; padding-top: 10px; border-top: 2px solid #111; font-size: 15px; }
  .footer { text-align: center; margin-top: 24px; font-size: 11px; color: #666; white-space: pre-line; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
  ${shopHeaderHtml(config)}
  ${opts.sousTitre ? `<div class="sub">${escapeHtml(opts.sousTitre)}</div>` : ""}
  ${lignesHtml}
  ${opts.total ? `<div class="total"><span>Total</span><span>${escapeHtml(opts.total)}</span></div>` : ""}
  ${pied ? `<div class="footer">${escapeHtml(pied)}</div>` : ""}
</body>
</html>`);
  win.document.close();
  win.focus();
  win.print();
}

/** Imprime un lot de tickets prépayés en coupons détachables (grille 2 colonnes),
 * chaque coupon portant l'en-tête du cybercafé — ils sont destinés à être découpés
 * et distribués séparément, l'en-tête doit donc être répétée sur chacun. */
export async function printTicketsBatch(tickets: { code: string; forfait: string }[]) {
  const win = window.open("", "_blank", "width=500,height=700");
  if (!win) return;

  const config = await fetchShopConfig();
  const nom = config["cybercafe.nom"] || "Cybercafé";
  const logo = config["cybercafe.logo"];
  const telephone = config["cybercafe.telephone"];

  const coupons = tickets
    .map(
      (t) => `<div class="coupon">
        ${logo ? `<img src="${logo}" alt="${escapeHtml(nom)}" class="logo" />` : ""}
        <div class="coupon-title">${escapeHtml(nom)}</div>
        ${telephone ? `<div class="coupon-tel">${escapeHtml(telephone)}</div>` : ""}
        <div class="coupon-forfait">${escapeHtml(t.forfait)}</div>
        <div class="coupon-code">${escapeHtml(t.code)}</div>
      </div>`
    )
    .join("");

  win.document.write(`<!doctype html><html><head><title>Tickets</title><meta charset="utf-8" />
    <style>
      body { font-family: "Courier New", monospace; margin: 0; padding: 16px; }
      .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
      .coupon { border: 1px dashed #333; border-radius: 8px; padding: 14px; text-align: center; }
      .coupon .logo { max-width: 60px; max-height: 40px; margin: 0 auto 4px; object-fit: contain; }
      .coupon-title { font-weight: bold; font-size: 13px; }
      .coupon-tel { font-size: 10px; color: #666; }
      .coupon-forfait { font-size: 12px; color: #555; margin: 4px 0; }
      .coupon-code { font-size: 18px; font-weight: bold; letter-spacing: 0.08em; margin-top: 8px; }
      @media print { .coupon { break-inside: avoid; } }
    </style>
    </head><body><div class="grid">${coupons}</div></body></html>`);
  win.document.close();
  win.focus();
  win.print();
}

function escapeHtml(value: string): string {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}
