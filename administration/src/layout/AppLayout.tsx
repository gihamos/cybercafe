import { useCallback, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Monitor, MessageCircle, Zap, Wallet, Users, Tags, ShieldCheck,
  Package, ShoppingBag, Percent, CreditCard, HardDrive, Printer, Gauge, History,
  Sun, Moon, LogOut, Search, BarChart3, Ticket, Settings, Eye, HardDriveDownload,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { usePermissions } from "../auth/usePermissions";
import { api } from "../api/client";
import { useAdminSocket } from "../ws/useAdminSocket";
import { applyTheme, getStoredTheme } from "../theme";
import DashboardPage from "../pages/DashboardPage";
import PostesPage from "../pages/PostesPage";
import ClientsPage from "../pages/ClientsPage";
import UserGroupsPage from "../pages/UserGroupsPage";
import EquipePage from "../pages/EquipePage";
import OffresPage from "../pages/OffresPage";
import ArticlesPage from "../pages/ArticlesPage";
import PromotionsPage from "../pages/PromotionsPage";
import CaissePage from "../pages/CaissePage";
import PaiementsPage from "../pages/PaiementsPage";
import ImpressionPage from "../pages/ImpressionPage";
import BandePassantePage from "../pages/BandePassantePage";
import HistoriquePage from "../pages/HistoriquePage";
import ChatPage from "../pages/ChatPage";
import StoragePage from "../pages/StoragePage";
import PayConnectPage from "../pages/PayConnectPage";
import StatistiquesPage from "../pages/StatistiquesPage";
import TicketsPage from "../pages/TicketsPage";
import ParametresPage from "../pages/ParametresPage";
import MonCompteModal from "../components/MonCompteModal";
import SurveillancePage from "../pages/SurveillancePage";
import LecteursBloquesPage from "../pages/LecteursBloquesPage";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { isAdmin, hasPermission } = usePermissions();
  const location = useLocation();
  const [theme, setTheme] = useState(getStoredTheme() ?? "light");
  const [unreadChat, setUnreadChat] = useState(0);
  const [pendingPayConnect, setPendingPayConnect] = useState(0);
  const [showMonCompte, setShowMonCompte] = useState(false);

  useEffect(() => {
    // deux familles de fils : postes (kiosque) + clients WiFi (portail)
    api.get<Record<string, number>>("/chat/non-lus")
      .then((data) => setUnreadChat((n) => n + Object.values(data).reduce((a, b) => a + b, 0)))
      .catch(() => {});
    api.get<{ non_lus: number }[]>("/chat/wifi/threads")
      .then((threads) => setUnreadChat((n) => n + threads.reduce((a, t) => a + t.non_lus, 0)))
      .catch(() => {});
    api.get<unknown[]>("/pay-connect/en-attente")
      .then((data) => setPendingPayConnect(data.length))
      .catch(() => {});
  }, []);

  useAdminSocket(
    useCallback((msg) => {
      if ((msg.type === "chat_message" || msg.type === "chat_message_wifi") && msg.data.expediteur === "client") {
        setUnreadChat((n) => n + 1);
      } else if (msg.type === "pay_connect_pending") {
        setPendingPayConnect((n) => n + 1);
      } else if (msg.type === "pay_connect_cancelled") {
        setPendingPayConnect((n) => Math.max(0, n - 1));
      }
    }, [])
  );

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    applyTheme(next);
  }

  const groups: NavGroup[] = [
    {
      label: "Vue d'ensemble",
      items: [
        { to: "/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
        { to: "/statistiques", label: "Statistiques", icon: BarChart3 },
      ],
    },
    {
      label: "Exploitation",
      items: [
        { to: "/postes", label: "Postes", icon: Monitor },
        ...(hasPermission("postes") ? [{ to: "/lecteurs-bloques", label: "Lecteurs bloqués", icon: HardDriveDownload }] : []),
        ...(hasPermission("surveillance") ? [{ to: "/surveillance", label: "Surveillance", icon: Eye }] : []),
        ...(hasPermission("chat") ? [{ to: "/chat", label: "Chat", icon: MessageCircle }] : []),
        { to: "/pay-connect", label: "Pay & Connect", icon: Zap },
        ...(hasPermission("caisse") ? [{ to: "/caisse", label: "Caisse", icon: Wallet }] : []),
      ],
    },
    {
      label: "Clients",
      items: [
        { to: "/clients", label: "Clients", icon: Users },
        ...(hasPermission("clients") ? [{ to: "/groupes", label: "Groupes", icon: Tags }] : []),
        ...(isAdmin ? [{ to: "/equipe", label: "Équipe", icon: ShieldCheck }] : []),
      ],
    },
    {
      label: "Catalogue & finances",
      items: [
        { to: "/offres", label: "Offres", icon: Package },
        ...(hasPermission("catalogue") ? [{ to: "/tickets", label: "Tickets", icon: Ticket }] : []),
        { to: "/articles", label: "Articles", icon: ShoppingBag },
        ...(hasPermission("catalogue") ? [{ to: "/promotions", label: "Promotions", icon: Percent }] : []),
        { to: "/paiements", label: "Paiements", icon: CreditCard },
        { to: "/stockage", label: "Stockage", icon: HardDrive },
      ],
    },
    {
      label: "Système",
      items: [
        { to: "/impression", label: "Impression", icon: Printer },
        ...(hasPermission("bande_passante") ? [{ to: "/bande-passante", label: "Bande passante", icon: Gauge }] : []),
        { to: "/historique", label: "Historique", icon: History },
        ...(isAdmin ? [{ to: "/parametres", label: "Paramètres", icon: Settings }] : []),
      ],
    },
  ];

  const currentLabel = groups.flatMap((g) => g.items).find((item) => location.pathname.startsWith(item.to))?.label;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark">
            <Zap size={16} />
          </div>
          <span className="sidebar-brand-name">Cybercafé</span>
        </div>
        <nav>
          {groups.map((group) => (
            <div key={group.label}>
              <div className="sidebar-section-label">{group.label}</div>
              {group.items.map((item) => (
                <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
                  <item.icon size={16} />
                  {item.label}
                  {item.to === "/chat" && unreadChat > 0 && (
                    <span className="sidebar-badge">{unreadChat > 99 ? "99+" : unreadChat}</span>
                  )}
                  {item.to === "/pay-connect" && pendingPayConnect > 0 && (
                    <span className="sidebar-badge">{pendingPayConnect}</span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="who" onClick={() => setShowMonCompte(true)} title="Modifier mon compte">
            <span className="avatar">{(user?.username || "?").slice(0, 2).toUpperCase()}</span>
            <span>
              {user?.username} <em style={{ opacity: 0.7 }}>({user?.role})</em>
            </span>
          </button>
          <button onClick={logout}>
            <LogOut size={14} /> Déconnexion
          </button>
        </div>
      </aside>

      {showMonCompte && <MonCompteModal onClose={() => setShowMonCompte(false)} />}

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-search">
            <Search size={14} />
            <span>{currentLabel || "Rechercher..."}</span>
          </div>
          <div className="topbar-actions">
            <button className="icon-btn" onClick={toggleTheme} title="Changer de thème">
              {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
            </button>
          </div>
        </header>

        <main className="content">
          <Routes>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="statistiques" element={<StatistiquesPage />} />
            <Route path="caisse" element={hasPermission("caisse") ? <CaissePage /> : <Navigate to="/dashboard" replace />} />
            <Route path="postes" element={<PostesPage />} />
            <Route path="lecteurs-bloques" element={hasPermission("postes") ? <LecteursBloquesPage /> : <Navigate to="/dashboard" replace />} />
            <Route path="surveillance" element={hasPermission("surveillance") ? <SurveillancePage /> : <Navigate to="/dashboard" replace />} />
            <Route path="chat" element={hasPermission("chat") ? <ChatPage /> : <Navigate to="/dashboard" replace />} />
            <Route path="pay-connect" element={<PayConnectPage />} />
            <Route path="stockage" element={<StoragePage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route path="groupes" element={hasPermission("clients") ? <UserGroupsPage /> : <Navigate to="/dashboard" replace />} />
            <Route path="offres" element={<OffresPage />} />
            <Route path="tickets" element={hasPermission("catalogue") ? <TicketsPage /> : <Navigate to="/dashboard" replace />} />
            <Route path="parametres" element={isAdmin ? <ParametresPage /> : <Navigate to="/dashboard" replace />} />
            <Route path="articles" element={<ArticlesPage />} />
            <Route path="promotions" element={hasPermission("catalogue") ? <PromotionsPage /> : <Navigate to="/dashboard" replace />} />
            <Route path="paiements" element={<PaiementsPage />} />
            <Route path="impression" element={<ImpressionPage />} />
            <Route path="bande-passante" element={hasPermission("bande_passante") ? <BandePassantePage /> : <Navigate to="/dashboard" replace />} />
            <Route path="historique" element={<HistoriquePage />} />
            <Route path="equipe" element={isAdmin ? <EquipePage /> : <Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
