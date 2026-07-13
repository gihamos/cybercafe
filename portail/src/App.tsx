import { Navigate, Route, Routes } from "react-router-dom";
import { usePortalAuth } from "./auth/PortalAuth";
import { useConfigPublique } from "./components/Brand";
import { CharteGate } from "./components/Charte";
import ConnexionPage from "./pages/ConnexionPage";
import AchatTicketPage from "./pages/AchatTicketPage";
import RechargePubliquePage from "./pages/RechargePubliquePage";
import TicketSessionPage from "./pages/TicketSessionPage";
import AppLayout from "./layout/AppLayout";

export default function App() {
  const { mode, loading, profil } = usePortalAuth();
  const config = useConfigPublique();

  if (loading) {
    return (
      <div className="public-shell">
        <p className="muted" style={{ marginTop: 80 }}>Chargement...</p>
      </div>
    );
  }

  // Session par code ticket : accès WiFi uniquement, pas d'espace compte
  if (mode === "ticket") {
    return (
      <Routes>
        <Route path="/wifi" element={<TicketSessionPage />} />
        <Route path="*" element={<Navigate to="/wifi" replace />} />
      </Routes>
    );
  }

  if (mode === "anonyme") {
    return (
      <Routes>
        <Route path="/connexion" element={<ConnexionPage />} />
        <Route path="/acheter-ticket" element={<AchatTicketPage />} />
        <Route path="/recharger" element={<RechargePubliquePage />} />
        <Route path="*" element={<Navigate to="/connexion" replace />} />
      </Routes>
    );
  }

  // charte configurée et jamais acceptée : étape bloquante avant l'espace client
  if (config?.charte?.trim() && profil && !profil.charte_acceptee) {
    return <CharteGate />;
  }

  // mode compte : toutes les fonctionnalités
  return <AppLayout />;
}
