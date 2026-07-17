import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  BarChart3, Home, LogOut, MessageCircle, Moon, Printer, Receipt,
  ShoppingBag, ShoppingCart, Sun, UserRound, Wifi, FolderOpen,
} from "lucide-react";
import { useState } from "react";
import { usePortalAuth } from "../auth/PortalAuth";
import { AnnonceBanner } from "../components/AnnonceBanner";
import { useCart } from "../cart/CartContext";
import { useConfigPublique } from "../components/Brand";
import { applyTheme, getStoredTheme } from "../theme";
import TableauBordPage from "../pages/TableauBordPage";
import ConsommationPage from "../pages/ConsommationPage";
import FacturesPage from "../pages/FacturesPage";
import BoutiquePage from "../pages/BoutiquePage";
import PanierPage from "../pages/PanierPage";
import ComptePage from "../pages/ComptePage";
import RechargePage from "../pages/RechargePage";
import ChatPage from "../pages/ChatPage";
import FichiersPage from "../pages/FichiersPage";
import ImpressionsPage from "../pages/ImpressionsPage";

export default function AppLayout() {
  const { profil, logout } = usePortalAuth();
  const { count } = useCart();
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
          <NavLink to="/panier" className="icon-btn" title="Mon panier">
            <ShoppingCart size={19} />
            {count > 0 && <span className="pastille">{count > 99 ? "99+" : count}</span>}
          </NavLink>
          <button className="icon-btn" onClick={toggleTheme} title="Changer de thème">
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button className="icon-btn" onClick={logout} title={`Déconnexion (${profil?.username})`}>
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <nav className="app-nav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          <Home size={19} /> Accueil
        </NavLink>
        <NavLink to="/boutique" className={({ isActive }) => (isActive ? "active" : "")}>
          <ShoppingBag size={19} /> Boutique
        </NavLink>
        <NavLink to="/consommation" className={({ isActive }) => (isActive ? "active" : "")}>
          <BarChart3 size={19} /> Suivi
        </NavLink>
        <NavLink to="/factures" className={({ isActive }) => (isActive ? "active" : "")}>
          <Receipt size={19} /> Factures
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => (isActive ? "active" : "")}>
          <MessageCircle size={19} /> Chat
        </NavLink>
        <NavLink to="/fichiers" className={({ isActive }) => (isActive ? "active" : "")}>
          <FolderOpen size={19} /> Fichiers
        </NavLink>
        <NavLink to="/impressions" className={({ isActive }) => (isActive ? "active" : "")}>
          <Printer size={19} /> Imprimer
        </NavLink>
        <NavLink to="/compte" className={({ isActive }) => (isActive ? "active" : "")}>
          <UserRound size={19} /> Compte
        </NavLink>
      </nav>

      <main className="app-content">
        <AnnonceBanner />
        <Routes>
          <Route index element={<TableauBordPage />} />
          <Route path="boutique" element={<BoutiquePage />} />
          <Route path="panier" element={<PanierPage />} />
          <Route path="consommation" element={<ConsommationPage />} />
          <Route path="factures" element={<FacturesPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="fichiers" element={<FichiersPage />} />
          <Route path="impressions" element={<ImpressionsPage />} />
          <Route path="compte" element={<ComptePage />} />
          <Route path="recharge" element={<RechargePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
