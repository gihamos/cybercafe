import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { API_BASE_URL, getToken } from "../api/client";

/** <img src> ne peut pas porter l'en-tête Authorization requis par l'API : on récupère
 * l'image en blob via fetch (comme downloadFile dans api/client.ts) puis on l'affiche
 * via une URL objet locale, révoquée au démontage. */
export function AuthenticatedImage({ path, alt, style, onClick }: {
  path: string;
  alt: string;
  style?: CSSProperties;
  onClick?: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    const token = getToken();

    fetch(`${API_BASE_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => (res.ok ? res.blob() : Promise.reject(res)))
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (!url) {
    return <div style={{ ...style, background: "var(--surface-2)" }} />;
  }
  return <img src={url} alt={alt} style={style} onClick={onClick} />;
}
