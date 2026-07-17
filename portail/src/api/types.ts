export interface ConfigPublique {
  nom: string | null;
  logo: string | null;
  devise: string | null;
  adresse: string | null;
  telephone: string | null;
  taux_tva: number | null;
  charte: string | null;
  titre_accueil: string | null;
  texte_accueil: string | null;
  message_info: string | null;
  message_connexion: string | null;
}

export interface Annonce {
  id: number;
  titre: string;
  message: string;
  date: string;
}

export interface OffrePublique {
  id: number;
  nom: string;
  description: string | null;
  type_offre: "temps" | "data" | "illimite";
  prix: number;
  duree_minutes: number | null;
  quota_mo: number | null;
  unite_duree: string | null;
  valeur_duree: number | null;
}

export interface TicketChoix {
  id: number;
  code: string;
  offre_nom: string | null;
  restant_minutes: number | null;
  restant_data_mo: number | null;
  date_expiration: string | null;
}

export interface SessionWifi {
  id: number;
  est_active: boolean;
  date_debut: string;
  date_fin: string | null;
  consommation_minutes: number;
  consommation_data_mo: number;
  limite_minutes: number | null;
  limite_data_mo: number | null;
  restant_minutes: number | null;
  illimite: boolean;
  ticket_code: string | null;
  token?: string;
}

export interface LimiteSessionsDetail {
  code: "limite_sessions_atteinte";
  portee: "ticket" | "forfait" | "compte";
  limite: number;
  session_a_deconnecter: { id: number; poste_nom: string | null; date_debut: string };
}

export interface AbonnementCourant {
  id: number;
  offre_nom: string | null;
  date_debut: string;
  date_fin: string | null;
  est_suspendu: boolean;
  illimite: boolean;
  minutes_par_jour: number | null;
  minutes_restantes_aujourdhui: number | null;
  data_totale_mo: number | null;
  data_restante_mo: number | null;
}

export interface MonProfil {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  address: string | null;
  date_of_born: string | null;
  solde_euros: number;
  date_create: string;
  abonnement_courant: AbonnementCourant | null;
  stockage: { quota_mo: number; usage_octets: number };
  charte_acceptee: boolean;
}

export interface ArticleBoutique {
  id: number;
  nom: string;
  description: string | null;
  prix: number;
  categorie_nom: string | null;
  categorie_emoji: string | null;
  stock: number | null;
  en_rupture: boolean;
  a_une_image: boolean;
}

export interface CommandeEnLigne {
  paiement_id: number;
  approval_url: string;
  secret: string;
  montant?: number;
}

export interface StatutCommande {
  paiement_id: number;
  statut: "en_attente" | "succes" | "echec" | "annule";
  montant: number;
  ticket_code?: string;
}

export interface ResultatPanier {
  total: number;
  lignes: { type: string; nom: string; quantite: number; prix_unitaire: number; tickets_codes?: string[] }[];
  nouveau_solde: number;
}

export interface SessionConso {
  id: number;
  poste_nom: string | null;
  date_debut: string;
  date_fin: string | null;
  est_active: boolean;
  consommation_minutes: number;
  consommation_data_mo: number;
}

export interface MaConsommation {
  total_minutes: number;
  total_data_mo: number;
  sessions: SessionConso[];
}

export interface MessageChat {
  id: number;
  expediteur: "client" | "operateur";
  message: string;
  date_envoi: string;
  lu: boolean;
}

export interface MonPaiement {
  id: number;
  montant: number;
  devise: string;
  type_paiement: string;
  statut: string;
  date_paiement: string;
  nature: "forfait" | "article" | "credit";
  libelle: string;
}

export interface FichierStocke {
  id: number;
  nom_original: string;
  taille_octets: number;
  content_type: string | null;
  date_upload: string;
}

export interface AchatArticleEntry {
  id: number;
  article_nom: string | null;
  prix: number;
  date_achat: string;
  statut_commande: "a_preparer" | "prete" | "recuperee";
  paiement_id: number | null;
}

export interface AchatForfaitEntry {
  id: number;
  offre_nom: string | null;
  prix: number | null;
  date_achat: string;
}

export interface MesAchats {
  articles: AchatArticleEntry[];
  forfaits: AchatForfaitEntry[];
}

export interface MonImpression {
  id: number;
  fichier_nom: string;
  pages_total: number | null;
  type_impression: string;
  recto_verso: boolean;
  prix_total: number | null;
  statut: string;
  paye?: boolean;
  date_impression: string;
}

export interface LignePanier {
  type: "article" | "forfait";
  id: number;
  nom: string;
  prix: number;
  quantite: number;
  emoji?: string | null;
  a_une_image?: boolean;
}
