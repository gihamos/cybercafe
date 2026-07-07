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
  categorie: string | null;
  actif: boolean;
  metadatas: Record<string, unknown> | null;
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

export type TypeProfilBP = "offre" | "abonnement" | "ticket" | "user" | "poste";

export interface BandePassanteProfil {
  id: number;
  type_profil: TypeProfilBP;
  offre_id: number | null;
  abonnement_id: number | null;
  ticket_id: number | null;
  user_id: number | null;
  poste_id: number | null;
  download_mbps: number | null;
  upload_mbps: number | null;
  quota_journalier_mo: number | null;
  quota_mensuel_mo: number | null;
  bloquer_si_depasse: boolean;
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
