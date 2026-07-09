export type UserRole = "admin" | "operateur" | "client";

export type TypePaiement = "especes" | "carte" | "mobile_money" | "virement" | "code_prepaye" | "gratuit" | "paypal";

export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  role: UserRole;
}

export type PosteEtat = "libre" | "occupe" | "bloque" | "hors_ligne";
export type TypePoste = "client" | "admin" | "serveur" | "borne_wifi";

export interface Poste {
  id: number;
  nom: string;
  description: string | null;
  type_poste: TypePoste;
  etat: PosteEtat;
  ip: string | null;
  mac_adresse: string | null;
  hostname: string | null;
  os: string | null;
  est_verrouille: boolean;
  est_en_ligne: boolean;
  derniere_activite: string;
  version_client: string | null;
  session_active?: SessionBrief | null;
}

export interface AbonnementCourant {
  id: number;
  offre_id: number;
  date_debut: string;
  date_fin: string | null;
  est_actif: boolean;
  est_suspendu: boolean;
  minutes_par_jour: number | null;
  minutes_restantes_aujourdhui: number | null;
  data_totale_mo: number | null;
  data_restante_mo: number | null;
  illimite: boolean;
}

export interface ClientUser {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  date_of_born: string | null;
  solde_euros: number;
  abonnement_courant: AbonnementCourant | null;
  offres_acheter: unknown[] | null;
  address: string | null;
  date_create: string;
  date_expire: string | null;
  is_active?: boolean;
  piece_identite_type?: string | null;
  piece_identite_numero?: string | null;
  piece_identite_organisme?: string | null;
  notes?: string | null;
  groupe_ids?: number[];
  groupe_noms?: string[];
}

export type ModeFiltrage = "liste_noire" | "liste_blanche";

export interface UserGroupEntry {
  id: number;
  nom: string;
  description: string | null;
  date_creation: string;
  mode_filtrage: ModeFiltrage;
  quota_stockage_mo: number | null;
  nb_membres: number;
}

export interface SessionBrief {
  id: number;
  user_id: number | null;
  ticket_id: number | null;
  limite_minutes: number | null;
  consommation_minutes: number;
  limite_data_mo: number | null;
  consommation_data_mo: number;
}

export type TypeOffre = "temps" | "data" | "illimite";
export type UniteDuree = "minute" | "heure" | "jour" | "hebdo" | "mois" | "annee";

export interface Offre {
  id: number;
  nom: string;
  type_offre: TypeOffre;
  prix: number;
  description: string | null;
  debit_upload_kbps: number | null;
  debit_download_kbps: number | null;
  unite_duree: UniteDuree | null;
  valeur_duree: number | null;
  is_actif: boolean;
  date_creation: string;
  date_expiration: string | null;
  duree_minutes?: number;
  quota_mo?: number;
}

export interface Article {
  id: number;
  nom: string;
  description: string | null;
  prix: number;
  categorie_id: number | null;
  categorie_nom: string | null;
  categorie_emoji: string | null;
  actif: boolean;
  metadatas: Record<string, unknown> | null;
  stock: number | null;
  stock_alerte: number | null;
}

export interface ArticleCategorieEntry {
  id: number;
  nom: string;
  emoji: string | null;
  description: string | null;
  date_creation: string;
  nb_articles: number;
}

export interface VenteArticle {
  id: number;
  article_id: number;
  article_nom: string | null;
  prix: number;
  user_id: number | null;
  user_nom: string | null;
  ticket_id: number | null;
  operateur_id: number | null;
  operateur_nom: string | null;
  paiement_id: number | null;
  date_achat: string;
}

export interface Promotion {
  id: number;
  nom: string;
  code: string | null;
  mecanisme: string;
  valeur: number;
  parametres: Record<string, unknown> | null;
  offre_id: number | null;
  article_id: number | null;
  date_debut: string;
  date_fin: string | null;
  usage_max: number | null;
  usage_count: number;
  actif: boolean;
  date_creation: string;
}

export type StatutPaiement = "succes" | "echec" | "annule" | "en_attente";

export interface Paiement {
  id: number;
  user_id: number | null;
  ticket_id: number | null;
  montant: number;
  devise: string;
  type_paiement: TypePaiement;
  statut: StatutPaiement;
  reference: string | null;
  date_paiement: string;
}

export type StatutImpression = "en_attente" | "en_cours" | "succes" | "echec" | "annulee";
export type TypeImpression = "noir_blanc" | "couleur";
export type OrigineImpression = "poste" | "wifi" | "mobile" | "portail_web";

export interface Impression {
  id: number;
  origine: OrigineImpression;
  user_id: number | null;
  ticket_id: number | null;
  poste_id: number | null;
  fichier_nom: string;
  pages_total: number;
  recto_verso: boolean;
  type_impression: TypeImpression;
  prix_par_page: number;
  prix_total: number;
  statut: StatutImpression;
  message_erreur: string | null;
  date_impression: string;
}

export interface SystemSetting {
  id: number;
  cle: string;
  categorie: string;
  valeur: unknown;
  description: string | null;
  date_modification: string;
}

export type TypeProfilBP = "offre" | "abonnement" | "ticket" | "user" | "poste" | "groupe";

export interface BandePassanteProfil {
  id: number;
  type_profil: TypeProfilBP;
  offre_id: number | null;
  abonnement_id: number | null;
  ticket_id: number | null;
  user_id: number | null;
  poste_id: number | null;
  groupe_id: number | null;
  download_mbps: number | null;
  upload_mbps: number | null;
  quota_journalier_mo: number | null;
  quota_mensuel_mo: number | null;
  bloquer_si_depasse: boolean;
}

export interface SiteRegleEntry {
  id: number;
  domaine: string;
  description: string | null;
  groupe_id: number | null;
  age_min: number | null;
  actif: boolean;
  date_creation: string;
}

export interface RevenuJour {
  date: string;
  total: number;
}

export interface ArticleVendu {
  nom: string;
  quantite: number;
  total: number;
}

export interface StatsResume {
  revenus_par_jour: RevenuJour[];
  revenu_total_30j: number;
  sessions_actives: number;
  sessions_aujourdhui: number;
  articles_plus_vendus: ArticleVendu[];
  nouveaux_clients_par_jour: { date: string; total: number }[];
  postes: { total: number; occupes: number; en_ligne: number; taux_occupation: number };
  total_clients: number;
}

export interface HistoriqueEntry {
  id: number;
  type_evenement: string;
  description: string;
  details: Record<string, unknown> | null;
  user_id: number | null;
  operateur_id: number | null;
  ticket_id: number | null;
  poste_id: number | null;
  timestamp: string;
}

export interface CaisseSession {
  id: number;
  operateur_id: number;
  montant_ouverture: number;
  date_ouverture: string;
  montant_cloture_theorique: number | null;
  montant_cloture_reel: number | null;
  ecart: number | null;
  date_cloture: string | null;
  est_ouverte: boolean;
  notes: string | null;
}

export interface CaisseVentilationEntry {
  nombre: number;
  total: number;
}

export interface CaisseResume {
  nb_transactions: number;
  total_general: number;
  ventilation: Record<string, CaisseVentilationEntry>;
}

export interface CaisseTransaction {
  id: number;
  montant: number;
  type_paiement: TypePaiement;
  statut: string;
  reference: string | null;
  user_id: number | null;
  ticket_id: number | null;
  date_paiement: string;
}

export interface EquipeUser {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: UserRole;
  is_active: boolean;
  date_create: string;
}

export type ExpediteurChat = "client" | "operateur";

export interface ChatMessageEntry {
  id: number;
  poste_id: number;
  expediteur: ExpediteurChat;
  operateur_id: number | null;
  message: string;
  date_envoi: string;
  lu: boolean;
}

export interface FichierStocke {
  id: number;
  nom_original: string;
  taille_octets: number;
  content_type: string | null;
  date_upload: string;
}

export interface QuotaInfo {
  quota_mo: number;
  usage_octets: number;
}

export type StatutPayConnect = "en_attente" | "confirme" | "refuse" | "annule";

export interface PayConnectRequestEntry {
  id: number;
  poste_id: number;
  minutes: number;
  montant: number;
  statut: StatutPayConnect;
  operateur_id: number | null;
  date_creation: string;
  date_traitement: string | null;
}

export interface VentesParCategorie {
  categorie_id: number;
  nom: string;
  emoji: string | null;
  quantite: number;
  total: number;
}

export interface UsageParPoste {
  poste_id: number;
  poste_nom: string;
  nb_sessions: number;
  minutes_totales: number;
}

export interface ClientsParGroupe {
  groupe_id: number | null;
  nom: string;
  nb_clients: number;
  revenu: number;
}

export interface StatsDetaille {
  periode: { debut: string; fin: string };
  revenus_par_jour: RevenuJour[];
  revenu_total: number;
  revenu_periode_precedente: number;
  variation_pct: number | null;
  ventes_par_categorie: VentesParCategorie[];
  usage_par_poste: UsageParPoste[];
  clients_par_groupe: ClientsParGroupe[];
  articles_plus_vendus: ArticleVendu[];
  nouveaux_clients: number;
}

export interface AbonnementEntry {
  id: number;
  user_id: number;
  achat_id: number;
  offre_id: number;
  date_debut: string;
  date_fin: string | null;
  est_actif: boolean;
  est_suspendu: boolean;
  minutes_par_jour: number | null;
  minutes_restantes_aujourdhui: number | null;
  data_totale_mo: number | null;
  data_restante_mo: number | null;
  illimite: boolean;
}

export interface SessionEntry {
  id: number;
  poste_id: number;
  user_id: number | null;
  ticket_id: number | null;
  abonnement_id: number | null;
  date_debut: string;
  date_fin: string | null;
  est_active: boolean;
  est_terminee: boolean;
  consommation_minutes: number;
  consommation_data_mo: number;
  limite_minutes: number | null;
  limite_data_mo: number | null;
}

export interface LimiteEffective {
  source: "user" | "groupe" | null;
  download_mbps: number | null;
  upload_mbps: number | null;
  quota_journalier_mo: number | null;
  quota_mensuel_mo: number | null;
  bloquer_si_depasse: boolean;
}

export type TypeTicket = "temps" | "data" | "wifi" | "poste" | "illimite";

export interface TicketEntry {
  id: number;
  code: string;
  description: string | null;
  type_ticket: TypeTicket;
  offre_id: number | null;
  offre_nom: string | null;
  date_achat: string;
  date_expiration: string | null;
  est_actif: boolean;
  est_consomme: boolean;
  restant_minutes: number | null;
  restant_data_mo: number | null;
}

export interface CybercafeConfig {
  "cybercafe.nom": string;
  "cybercafe.logo": string | null;
  "cybercafe.adresse": string | null;
  "cybercafe.siret": string | null;
  "cybercafe.telephone": string | null;
  "cybercafe.email": string | null;
  "cybercafe.devise": string;
  "cybercafe.pied_recu": string;
  "chat.taille_max_fichier_mo": number;
}
