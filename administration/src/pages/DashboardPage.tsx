import { useAuth } from "../auth/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="page">
      <h1>Tableau de bord</h1>
      <p>
        Connecté en tant que <strong>{user?.username}</strong> ({user?.role}).
      </p>
    </div>
  );
}
