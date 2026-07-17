export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

const TOKEN_KEY = "portail_token";
const TICKET_TOKEN_KEY = "portail_ticket_token";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Jeton distinct pour le mode ticket (anonyme) — voir dependencies/access.py::get_current_ticket
// côté serveur : ce n'est pas un compte, il ne doit jamais être confondu avec TOKEN_KEY
// (sinon la vérification du profil compte au chargement de la page effacerait ce jeton).
export function getTicketToken(): string | null {
  return localStorage.getItem(TICKET_TOKEN_KEY);
}

export function setTicketToken(token: string | null) {
  if (token) localStorage.setItem(TICKET_TOKEN_KEY, token);
  else localStorage.removeItem(TICKET_TOKEN_KEY);
}

// Le serveur ne renvoie pas un format d'erreur unique : selon le router c'est soit
// {"detail": "message"} soit {"detail": {"error": true, "message": "..."}}.
function extractErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const anyBody = body as Record<string, unknown>;
  if (typeof anyBody.detail === "string") return anyBody.detail;
  if (anyBody.detail && typeof anyBody.detail === "object") {
    const detail = anyBody.detail as Record<string, unknown>;
    if (typeof detail.message === "string") return detail.message;
    if (detail.code === "limite_sessions_atteinte") return "Nombre maximum de connexions simultanées atteint";
  }
  if (typeof anyBody.message === "string") return anyBody.message;
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // /portail/ticket/* est protégé par un jeton de session ticket distinct du jeton
  // de compte (voir getTicketToken) — tout le reste utilise le jeton de compte normal.
  const token = path.startsWith("/portail/ticket/") ? getTicketToken() : getToken();
  // Pour un FormData (upload de fichier), ne PAS fixer Content-Type : le navigateur
  // doit poser lui-même le boundary multipart/form-data, un override le casserait.
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (res.status === 401) {
    window.dispatchEvent(new Event("cybercafe:unauthorized"));
  }

  if (!res.ok) {
    const detail = body && typeof body === "object" ? (body as Record<string, unknown>).detail : undefined;
    throw new ApiError(extractErrorMessage(body, `Erreur ${res.status}`), res.status, detail);
  }

  // La plupart des endpoints renvoient { status_code, data }, quelques-uns renvoient
  // directement l'objet (ex: POST /user/createClient) ou un autre champ (auth: "token").
  if (body && typeof body === "object" && "data" in (body as Record<string, unknown>)) {
    return (body as Record<string, unknown>).data as T;
  }
  return body as T;
}

export const api = {
  get: <T,>(path: string) => request<T>(path, { method: "GET" }),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T,>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T,>(path: string, file: File, fields?: Record<string, string>) => {
    const formData = new FormData();
    formData.append("file", file);
    if (fields) for (const [k, v] of Object.entries(fields)) formData.append(k, v);
    return request<T>(path, { method: "POST", body: formData });
  },
};

/** Télécharge un fichier protégé par JWT (impossible avec un simple lien <a href>, qui
 * ne peut pas porter l'en-tête Authorization) : on récupère le blob puis on déclenche
 * un téléchargement navigateur via une URL objet temporaire. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new ApiError(`Échec du téléchargement (${res.status})`, res.status);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
