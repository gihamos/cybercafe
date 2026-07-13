import { useEffect, useState } from "react";
import { Megaphone } from "lucide-react";
import { api } from "../api/client";
import { useConfigPublique } from "./Brand";
import type { Annonce } from "../api/types";

/** Bannière d'information : message général configuré + annonces diffusées par
 * l'équipe depuis le panneau d'administration. */
export function AnnonceBanner() {
  const config = useConfigPublique();
  const [annonces, setAnnonces] = useState<Annonce[]>([]);

  useEffect(() => {
    api.get<Annonce[]>("/portail/public/annonces").then(setAnnonces).catch(() => {});
    const interval = setInterval(() => {
      api.get<Annonce[]>("/portail/public/annonces").then(setAnnonces).catch(() => {});
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const derniere = annonces[0];
  if (!config?.message_info && !derniere) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {config?.message_info && (
        <div
          className="card"
          style={{
            padding: "10px 14px", fontSize: 13.5, display: "flex", gap: 10, alignItems: "flex-start",
            borderColor: "color-mix(in srgb, var(--accent) 40%, var(--border))",
          }}
        >
          <Megaphone size={16} style={{ color: "var(--accent)", flexShrink: 0, marginTop: 1 }} />
          <span style={{ whiteSpace: "pre-line" }}>{config.message_info}</span>
        </div>
      )}
      {derniere && (
        <div className="card" style={{ padding: "10px 14px", fontSize: 13.5, display: "flex", gap: 10, alignItems: "flex-start" }}>
          <Megaphone size={16} style={{ color: "var(--warning)", flexShrink: 0, marginTop: 1 }} />
          <span>
            <strong>{derniere.titre}</strong> — <span style={{ whiteSpace: "pre-line" }}>{derniere.message}</span>
          </span>
        </div>
      )}
    </div>
  );
}
