import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { LogOut, MessageCircle, Moon, Printer, Sun, Wifi } from "lucide-react";
import { useState } from "react";
import { usePortalAuth } from "../auth/PortalAuth";
import { AnnonceBanner } from "../components/AnnonceBanner";
import { useConfigPublique } from "../components/Brand";
import { applyTheme, getStoredTheme } from "../theme";
import TicketSessionPage from "../pages/TicketSessionPage";
import TicketChatPage from "../pages/TicketChatPage";
import TicketImpressionPage from "../pages/TicketImpressionPage";

/** Mise en page du mode ticket (connexion anonyme par code) — un sous-ensemble
 * volontairement réduit du mode compte : statut WiFi, chat avec l'accueil,
 * impression. Pas d'espace fichiers persistant ni de boutique (pas de solde à
 * débiter en mode anonyme). */
export default function TicketLayout() {
  const { ticketCode, logout } = usePortalAuth();
  const config = useConfigPublique();
  const [theme, setTheme] = useState(getStoredTheme() ?? "light");

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    applyTheme(next);
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <span className="titre">
          <Wifi size={19} style={{ color: "var(--accent)" }} /> {config?.nom || "Portail WiFi"}
        </span>
        <div className="topbar-actions">
          <button className="icon-btn" onClick={toggleTheme} title="Changer de thème">
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button className="icon-btn" onClick={logout} title={`Déconnexion (ticket ${ticketCode})`}>
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <nav className="app-nav">
        <NavLink to="/wifi" className={({ isActive }) => (isActive ? "active" : "")}>
          <Wifi size={19} /> WiFi
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => (isActive ? "active" : "")}>
          <MessageCircle size={19} /> Chat
        </NavLink>
        <NavLink to="/imprimer" className={({ isActive }) => (isActive ? "active" : "")}>
          <Printer size={19} /> Imprimer
        </NavLink>
      </nav>

      <main className="app-content">
        <AnnonceBanner />
        <Routes>
          <Route path="wifi" element={<TicketSessionPage />} />
          <Route path="chat" element={<TicketChatPage />} />
          <Route path="imprimer" element={<TicketImpressionPage />} />
          <Route path="*" element={<Navigate to="/wifi" replace />} />
        </Routes>
      </main>
    </div>
  );
}
