import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, getToken, setToken } from "../api/client";
import type { MonProfil, SessionWifi } from "../api/types";

const TICKET_KEY = "portail_ticket_code";

/** Trois états d'identification sur le portail :
 *  - anonyme (pages publiques : achat de ticket, recharge, connexion)
 *  - compte client (JWT) : toutes les fonctionnalités
 *  - ticket (le code fait office d'identifiant) : session WiFi uniquement */
interface PortalAuthState {
  mode: "anonyme" | "compte" | "ticket";
  profil: MonProfil | null;
  ticketCode: string | null;
  loading: boolean;
  loginCompte: (username: string, password: string) => Promise<void>;
  loginTicket: (code: string) => Promise<SessionWifi>;
  logout: () => void;
  rechargerProfil: () => Promise<void>;
}

const Ctx = createContext<PortalAuthState | null>(null);

export function PortalAuthProvider({ children }: { children: ReactNode }) {
  const [profil, setProfil] = useState<MonProfil | null>(null);
  const [ticketCode, setTicketCode] = useState<string | null>(() => localStorage.getItem(TICKET_KEY));
  const [loading, setLoading] = useState(true);

  const rechargerProfil = useCallback(async () => {
    if (!getToken()) return;
    const data = await api.get<MonProfil>("/portail/moi");
    setProfil(data);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        if (getToken()) await rechargerProfil();
      } catch {
        setToken(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [rechargerProfil]);

  useEffect(() => {
    const onUnauthorized = () => {
      setToken(null);
      setProfil(null);
    };
    window.addEventListener("cybercafe:unauthorized", onUnauthorized);
    return () => window.removeEventListener("cybercafe:unauthorized", onUnauthorized);
  }, []);

  async function loginCompte(username: string, password: string) {
    // l'endpoint auth renvoie {status_code, token} (pas de champ data)
    const result = await api.post<{ token: string }>(
      `/auth/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
    );
    if (!result?.token) throw new Error("Réponse d'authentification inattendue");
    setToken(result.token);
    await rechargerProfil();
  }

  async function loginTicket(code: string): Promise<SessionWifi> {
    const session = await api.post<SessionWifi>("/portail/wifi/connexion", { code });
    localStorage.setItem(TICKET_KEY, code.trim().toUpperCase());
    setTicketCode(code.trim().toUpperCase());
    return session;
  }

  function logout() {
    setToken(null);
    setProfil(null);
    localStorage.removeItem(TICKET_KEY);
    setTicketCode(null);
  }

  const mode = profil ? "compte" : ticketCode ? "ticket" : "anonyme";

  return (
    <Ctx.Provider value={{ mode, profil, ticketCode, loading, loginCompte, loginTicket, logout, rechargerProfil }}>
      {children}
    </Ctx.Provider>
  );
}

export function usePortalAuth(): PortalAuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePortalAuth hors du provider");
  return ctx;
}
