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

/** Ouvre (et lance l'impression de) un document HTML protégé par JWT dans un
 * nouvel onglet — utilisé pour les tickets de caisse imprimables, impossibles à
 * charger via un simple window.open(url) qui ne porte pas l'en-tête Authorization. */
export async function openAuthenticatedHtml(path: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new ApiError(`Document indisponible (${res.status})`, res.status);
  }
  const html = await res.text();
  const win = window.open("", "_blank", "width=380,height=640");
  if (!win) return;
  win.document.write(html);
  win.document.close();
  win.focus();
  win.print();
}
