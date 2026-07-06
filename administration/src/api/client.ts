export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

const TOKEN_KEY = "cybercafe_token";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
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
  }
  if (typeof anyBody.message === "string") return anyBody.message;
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
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
    throw new ApiError(extractErrorMessage(body, `Erreur ${res.status}`), res.status);
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
};
