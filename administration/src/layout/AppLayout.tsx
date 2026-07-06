import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import DashboardPage from "../pages/DashboardPage";
import PostesPage from "../pages/PostesPage";
import ClientsPage from "../pages/ClientsPage";
import EquipePage from "../pages/EquipePage";
import OffresPage from "../pages/OffresPage";
import ArticlesPage from "../pages/ArticlesPage";
import PromotionsPage from "../pages/PromotionsPage";
import CaissePage from "../pages/CaissePage";
import PaiementsPage from "../pages/PaiementsPage";
import ImpressionPage from "../pages/ImpressionPage";
import BandePassantePage from "../pages/BandePassantePage";
import HistoriquePage from "../pages/HistoriquePage";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "admin";

  const navItems = [
    { to: "/dashboard", label: "Tableau de bord" },
    { to: "/caisse", label: "Caisse" },
    { to: "/postes", label: "Postes" },
    { to: "/clients", label: "Clients" },
    { to: "/offres", label: "Offres" },
    { to: "/articles", label: "Articles" },
    { to: "/promotions", label: "Promotions" },
    { to: "/paiements", label: "Paiements" },
    { to: "/impression", label: "Impression" },
    { to: "/bande-passante", label: "Bande passante" },
    { to: "/historique", label: "Historique" },
    ...(isAdmin ? [{ to: "/equipe", label: "Équipe" }] : []),
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h2>Cybercafé</h2>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>
            {user?.username} <em>({user?.role})</em>
          </span>
          <button className="btn btn-sm" onClick={logout}>Déconnexion</button>
        </div>
      </aside>
      <main className="content">
        <Routes>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="caisse" element={<CaissePage />} />
          <Route path="postes" element={<PostesPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="offres" element={<OffresPage />} />
          <Route path="articles" element={<ArticlesPage />} />
          <Route path="promotions" element={<PromotionsPage />} />
          <Route path="paiements" element={<PaiementsPage />} />
          <Route path="impression" element={<ImpressionPage />} />
          <Route path="bande-passante" element={<BandePassantePage />} />
          <Route path="historique" element={<HistoriquePage />} />
          <Route path="equipe" element={isAdmin ? <EquipePage /> : <Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
