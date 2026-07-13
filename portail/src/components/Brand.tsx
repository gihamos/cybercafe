import { useEffect, useState } from "react";
import { Wifi } from "lucide-react";
import { api } from "../api/client";
import type { ConfigPublique } from "../api/types";

let configCache: ConfigPublique | null = null;

export function useConfigPublique(): ConfigPublique | null {
  const [config, setConfig] = useState<ConfigPublique | null>(configCache);
  useEffect(() => {
    if (configCache) return;
    api
      .get<ConfigPublique>("/portail/public/config")
      .then((c) => {
        configCache = c;
        setConfig(c);
      })
      .catch(() => {});
  }, []);
  return config;
}

export function Brand({ sousTitre, accueil = false }: { sousTitre?: string; accueil?: boolean }) {
  const config = useConfigPublique();
  const titre = (accueil && config?.titre_accueil?.trim()) || config?.nom || "Portail WiFi";
  const texte = (accueil && config?.texte_accueil?.trim()) || sousTitre;
  return (
    <div className="brand fade-in">
      {config?.logo ? (
        <img className="logo" src={config.logo} alt={config?.nom || "Cybercafé"} />
      ) : (
        <div className="brand-mark">
          <Wifi size={26} />
        </div>
      )}
      <h1>{titre}</h1>
      {texte && <span className="muted" style={{ whiteSpace: "pre-line" }}>{texte}</span>}
    </div>
  );
}
