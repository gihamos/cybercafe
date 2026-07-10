import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "./AuthContext";

/** Permissions "avancées" — opt-in, jamais incluses dans l'accès complet implicite
 * d'un opérateur non restreint (permissions === null). L'administrateur doit les
 * ajouter explicitement à la liste d'un opérateur pour les lui déléguer. Doit rester
 * synchronisé avec PERMISSIONS_AVANCEES dans server/services/permission_service.py. */
const PERMISSIONS_AVANCEES = new Set(["gestion_stock", "creation_forfaits"]);

/** Expose isAdmin/hasPermission à n'importe quelle page, pour masquer les actions que
 * l'utilisateur courant n'a pas le droit d'effectuer (pas seulement les items de nav) —
 * cohérent avec les permissions vérifiées côté serveur (require_permission). */
export function usePermissions() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [permissions, setPermissions] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    api.get<{ permissions: string[] | null }>("/user/me/permissions")
      .then((data) => setPermissions(data.permissions))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  function hasPermission(cle: string): boolean {
    if (isAdmin) return true;
    if (PERMISSIONS_AVANCEES.has(cle)) {
      return permissions !== null && permissions.includes(cle);
    }
    return permissions === null || permissions.includes(cle);
  }

  return { isAdmin, permissions, hasPermission, loading };
}
