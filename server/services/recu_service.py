import html

from sqlalchemy.orm import Session

from models.paiement import Paiement
from models.achat_article import AchatArticle
from services.config_service import ConfigService


class RecuService:
    """Reçu (ticket de caisse) HTML autonome, téléchargeable par le client depuis le
    portail WiFi ou le poste kiosque — pour un paiement (article, forfait, recharge,
    bon de crédit, panier). Anonymisé : nom/prénom du client, jamais l'opérateur ni le
    username (mêmes règles que les reçus imprimés du panneau d'administration)."""

    @staticmethod
    def _nom_client(paiement: Paiement) -> str:
        if paiement.user:
            nom = " ".join(p for p in [paiement.user.first_name, paiement.user.last_name] if p)
            return nom or paiement.user.username
        if paiement.ticket:
            return f"Ticket {paiement.ticket.code}"
        return "—"

    @staticmethod
    def _objet(db: Session, paiement: Paiement) -> str | None:
        if paiement.achat_id and paiement.achat and paiement.achat.offre:
            return f"Forfait {paiement.achat.offre.nom}"
        achat_article = db.query(AchatArticle).filter(AchatArticle.paiement_id == paiement.id).first()
        if achat_article and achat_article.article:
            return f"Article {achat_article.article.nom}"
        if (paiement.details or {}).get("intent") == "recharge_solde":
            return "Recharge de solde"
        if paiement.type_paiement == "code_prepaye" or (
            hasattr(paiement.type_paiement, "value") and paiement.type_paiement.value == "code_prepaye"
        ):
            return "Recharge par bon de crédit"
        return None

    @staticmethod
    def generer_html(db: Session, paiement: Paiement) -> str:
        config = ConfigService.get_config(db)
        nom_shop = config.get("cybercafe.nom") or "Cybercafé"
        taux_tva = config.get("cybercafe.taux_tva")
        pied = config.get("cybercafe.pied_recu")

        entete = [config.get("cybercafe.adresse"), config.get("cybercafe.telephone"),
                  f"SIRET {config['cybercafe.siret']}" if config.get("cybercafe.siret") else None]
        entete_html = "".join(f"<div>{html.escape(l)}</div>" for l in entete if l)

        lignes = [
            ("Référence", paiement.reference or f"#{paiement.id}"),
            ("Client", RecuService._nom_client(paiement)),
        ]
        objet = RecuService._objet(db, paiement)
        if objet:
            lignes.append(("Objet", objet))
        type_p = paiement.type_paiement.value if hasattr(paiement.type_paiement, "value") else str(paiement.type_paiement)
        lignes.append(("Moyen", type_p))
        for pp in paiement.promotions_appliquees:
            lignes.append((f"Promo{f' ({pp.promotion.code})' if pp.promotion.code else ''} — {pp.promotion.nom}",
                           f"-{pp.montant_reduction:.2f}€"))
        lignes.append(("Date", paiement.date_paiement.strftime("%d/%m/%Y %H:%M")))

        lignes_html = "".join(
            f'<div class="row"><span>{html.escape(str(l))}</span><span>{html.escape(str(v))}</span></div>'
            for l, v in lignes
        )

        tva_html = ""
        if taux_tva:
            ht = paiement.montant / (1 + taux_tva / 100)
            tva = paiement.montant - ht
            tva_html = (
                f'<div class="row muted"><span>Total HT</span><span>{ht:.2f}€</span></div>'
                f'<div class="row muted"><span>dont TVA ({taux_tva}%)</span><span>{tva:.2f}€</span></div>'
            )

        return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Reçu {paiement.id}</title>
<style>
  body {{ font-family: "Courier New", monospace; font-size: 13px; max-width: 340px; margin: 0 auto; padding: 20px; color: #111; }}
  h1 {{ font-size: 16px; text-align: center; margin: 0 0 2px; }}
  .coordonnees {{ text-align: center; color: #555; font-size: 11px; line-height: 1.5; margin-bottom: 10px; }}
  .sub {{ text-align: center; color: #555; margin-bottom: 18px; font-size: 12px; }}
  .row {{ display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dashed #ccc; }}
  .muted {{ color: #777; font-size: 12px; }}
  .total {{ display: flex; justify-content: space-between; font-weight: bold; margin-top: 12px; padding-top: 10px; border-top: 2px solid #111; font-size: 15px; }}
  .footer {{ text-align: center; margin-top: 24px; font-size: 11px; color: #666; white-space: pre-line; }}
  @media print {{ body {{ padding: 0; }} }}
</style></head><body>
  <h1>{html.escape(nom_shop)}</h1>
  {f'<div class="coordonnees">{entete_html}</div>' if entete_html else ''}
  <div class="sub">Reçu de paiement</div>
  {lignes_html}
  <div class="total"><span>Total TTC</span><span>{paiement.montant:.2f}€</span></div>
  {tva_html}
  {f'<div class="footer">{html.escape(pied)}</div>' if pied else ''}
</body></html>"""


    # ---------------------------------------------------------
    # TICKET DE CAISSE (vente groupée, caisse professionnelle)
    # ---------------------------------------------------------
    @staticmethod
    def generer_ticket_caisse_html(db: Session, vente) -> str:
        """Ticket de caisse imprimable : infos du magasin, lignes de produits,
        TVA, codes des tickets/bons générés, politique de remboursement et
        code-barres Code 128 de la référence (scannable pour un remboursement)."""
        from utils.code128 import code128_svg

        config = ConfigService.get_config(db)
        nom_shop = config.get("cybercafe.nom") or "Cybercafé"
        taux_tva = config.get("cybercafe.taux_tva")
        pied = config.get("cybercafe.pied_recu")
        politique = config.get("caisse.politique_remboursement")
        validite = config.get("caisse.validite_ticket_jours")

        entete = [config.get("cybercafe.adresse"), config.get("cybercafe.telephone"),
                  f"SIRET {config['cybercafe.siret']}" if config.get("cybercafe.siret") else None]
        entete_html = "".join(f"<div>{html.escape(l)}</div>" for l in entete if l)

        lignes_html = ""
        codes_html = ""
        for ligne in vente.lignes:
            rembourse = ""
            if ligne.quantite_remboursee:
                rembourse = f'<div class="muted">dont {ligne.quantite_remboursee} remboursé(s)</div>'
            lignes_html += (
                f'<div class="row"><span>{html.escape(ligne.designation)}'
                f'{f" × {ligne.quantite}" if ligne.quantite > 1 else ""}{rembourse}</span>'
                f'<span>{ligne.prix_unitaire * ligne.quantite:.2f}€</span></div>'
            )
            if ligne.ticket:
                nature = "Bon de recharge" if ligne.type_ligne.value == "bon" else "Code de connexion"
                codes_html += (
                    f'<div class="code-ticket"><span>{nature} — {html.escape(ligne.designation)}</span>'
                    f'<strong>{html.escape(ligne.ticket.code)}</strong></div>'
                )

        tva_html = ""
        if taux_tva:
            ht = vente.total / (1 + taux_tva / 100)
            tva_html = (
                f'<div class="row muted"><span>Total HT</span><span>{ht:.2f}€</span></div>'
                f'<div class="row muted"><span>dont TVA ({taux_tva}%)</span><span>{vente.total - ht:.2f}€</span></div>'
            )

        rembourse_html = ""
        if vente.montant_rembourse:
            rembourse_html = (
                f'<div class="row" style="color:#b00"><span>Remboursé</span>'
                f'<span>-{vente.montant_rembourse:.2f}€</span></div>'
            )

        client_html = ""
        if vente.user:
            nom_client = " ".join(p for p in [vente.user.first_name, vente.user.last_name] if p) or vente.user.username
            client_html = f'<div class="row"><span>Client</span><span>{html.escape(nom_client)}</span></div>'

        barcode = code128_svg(vente.reference)

        return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Ticket {html.escape(vente.reference)}</title>
<style>
  body {{ font-family: "Courier New", monospace; font-size: 13px; max-width: 340px; margin: 0 auto; padding: 20px; color: #111; }}
  h1 {{ font-size: 16px; text-align: center; margin: 0 0 2px; }}
  .coordonnees {{ text-align: center; color: #555; font-size: 11px; line-height: 1.5; margin-bottom: 10px; }}
  .sub {{ text-align: center; color: #555; margin-bottom: 14px; font-size: 12px; }}
  .row {{ display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dashed #ccc; }}
  .muted {{ color: #777; font-size: 12px; }}
  .total {{ display: flex; justify-content: space-between; font-weight: bold; margin-top: 12px; padding-top: 10px; border-top: 2px solid #111; font-size: 15px; }}
  .code-ticket {{ display: flex; justify-content: space-between; gap: 8px; padding: 6px 8px; margin-top: 6px; border: 1px dashed #555; border-radius: 6px; font-size: 12px; }}
  .code-ticket strong {{ letter-spacing: 0.12em; }}
  .barcode {{ text-align: center; margin-top: 18px; }}
  .barcode .ref {{ font-size: 12px; letter-spacing: 0.15em; margin-top: 4px; }}
  .politique {{ text-align: center; margin-top: 14px; font-size: 10.5px; color: #666; white-space: pre-line; }}
  .footer {{ text-align: center; margin-top: 10px; font-size: 11px; color: #666; white-space: pre-line; }}
  @media print {{ body {{ padding: 0; }} }}
</style></head><body>
  <h1>{html.escape(nom_shop)}</h1>
  {f'<div class="coordonnees">{entete_html}</div>' if entete_html else ''}
  <div class="sub">Ticket de caisse — {vente.date_vente.strftime("%d/%m/%Y %H:%M")}</div>
  {client_html}
  {lignes_html}
  {rembourse_html}
  <div class="total"><span>Total TTC</span><span>{vente.total:.2f}€</span></div>
  {tva_html}
  <div class="row muted"><span>Moyen de paiement</span><span>{html.escape(str(vente.type_paiement))}</span></div>
  {codes_html}
  <div class="barcode">{barcode}<div class="ref">{html.escape(vente.reference)}</div></div>
  {f'<div class="politique">{html.escape(politique)}{f" Ticket valable {int(validite)} jours." if validite else ""}</div>' if politique else ''}
  {f'<div class="footer">{html.escape(pied)}</div>' if pied else ''}
</body></html>"""
