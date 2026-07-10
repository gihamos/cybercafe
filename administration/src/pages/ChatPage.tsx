import { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, Paperclip, Download, File as FileIcon } from "lucide-react";
import type { ChangeEvent, FormEvent } from "react";
import { api, ApiError, downloadFile } from "../api/client";
import type { ChatMessageEntry, CybercafeConfig, Poste } from "../api/types";
import { useAdminSocket } from "../ws/useAdminSocket";

function formatTaille(octets: number): string {
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${(octets / 1024).toFixed(1)} Ko`;
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function ChatPage() {
  const [postes, setPostes] = useState<Poste[]>([]);
  const [nonLus, setNonLus] = useState<Record<number, number>>({});
  const [selectedPosteId, setSelectedPosteId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessageEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tailleMaxMo, setTailleMaxMo] = useState(5);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.get<Poste[]>("/poste/").then(setPostes).catch(() => {});
    api.get<Record<string, number>>("/chat/non-lus").then((data) => {
      setNonLus(Object.fromEntries(Object.entries(data).map(([k, v]) => [Number(k), v])));
    }).catch(() => {});
    api.get<CybercafeConfig>("/config/cybercafe").then((c) => {
      setTailleMaxMo(c["chat.taille_max_fichier_mo"]);
    }).catch(() => {});
  }, []);

  const loadHistorique = useCallback(async (posteId: number) => {
    setSelectedPosteId(posteId);
    setError(null);
    try {
      const data = await api.get<ChatMessageEntry[]>(`/chat/poste/${posteId}`);
      setMessages(data);
      setNonLus((prev) => ({ ...prev, [posteId]: 0 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur de chargement");
    }
  }, []);

  useAdminSocket(
    useCallback(
      (msg) => {
        if (msg.type === "chat_message") {
          const entry: ChatMessageEntry = msg.data;
          if (entry.poste_id === selectedPosteId) {
            // Le message peut déjà avoir été ajouté localement par handleSend (réponse
            // REST) avant que ce même message ne revienne via la diffusion WebSocket.
            setMessages((prev) => (prev.some((m) => m.id === entry.id) ? prev : [...prev, entry]));
          } else if (entry.expediteur === "client") {
            setNonLus((prev) => ({ ...prev, [entry.poste_id]: (prev[entry.poste_id] || 0) + 1 }));
          }
        }
      },
      [selectedPosteId]
    )
  );

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || !selectedPosteId) return;
    setSending(true);
    try {
      const msg = await api.post<ChatMessageEntry>(`/chat/poste/${selectedPosteId}/message`, { message: input.trim() });
      setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
      setInput("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Échec de l'envoi");
    } finally {
      setSending(false);
    }
  }

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !selectedPosteId) return;

    if (file.size > tailleMaxMo * 1024 * 1024) {
      setError(`Fichier trop volumineux (limite : ${tailleMaxMo} Mo)`);
      return;
    }

    setError(null);
    setSending(true);
    try {
      const msg = await api.upload<ChatMessageEntry>(
        `/chat/poste/${selectedPosteId}/message-fichier`, file, { message: input.trim() }
      );
      setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
      setInput("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Échec de l'envoi du fichier");
    } finally {
      setSending(false);
    }
  }

  async function handleDownload(m: ChatMessageEntry) {
    if (!m.piece_jointe_nom) return;
    try {
      await downloadFile(`/chat/message/${m.id}/piece-jointe`, m.piece_jointe_nom);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Échec du téléchargement");
    }
  }

  return (
    <div className="page">
      <h1>
          <MessageCircle size={20} /> Chat
        </h1>
      <p className="muted">Discussion en direct avec les postes — répondez aux demandes d'aide des clients.</p>

      {error && <p className="error">{error}</p>}

      <div style={{ display: "flex", gap: 16, height: 560 }}>
        <div className="card" style={{ width: 260, overflowY: "auto", padding: 8 }}>
          {postes.map((p) => (
            <div
              key={p.id}
              onClick={() => loadHistorique(p.id)}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "10px 12px", borderRadius: 8, cursor: "pointer",
                background: selectedPosteId === p.id ? "var(--accent-bg)" : "transparent",
              }}
            >
              <span>{p.nom}</span>
              {!!nonLus[p.id] && <span className="badge badge-danger">{nonLus[p.id]}</span>}
            </div>
          ))}
          {postes.length === 0 && <div className="empty-state">Aucun poste</div>}
        </div>

        <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {!selectedPosteId ? (
            <div className="empty-state">Sélectionnez un poste pour voir la discussion</div>
          ) : (
            <>
              <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
                {messages.map((m) => (
                  <div key={m.id} style={{ display: "flex", justifyContent: m.expediteur === "operateur" ? "flex-end" : "flex-start" }}>
                    <div
                      style={{
                        maxWidth: "70%", padding: "8px 12px", borderRadius: 10,
                        background: m.expediteur === "operateur" ? "var(--accent)" : "var(--bg)",
                        color: m.expediteur === "operateur" ? "white" : "var(--text)",
                      }}
                    >
                      {m.message && <div>{m.message}</div>}
                      {m.piece_jointe_nom && (
                        <button
                          type="button"
                          onClick={() => handleDownload(m)}
                          style={{
                            display: "flex", alignItems: "center", gap: 6, marginTop: m.message ? 6 : 0,
                            background: "rgba(255,255,255,0.12)", border: "none", borderRadius: 6,
                            padding: "6px 8px", cursor: "pointer", color: "inherit", width: "100%",
                          }}
                        >
                          <FileIcon size={14} />
                          <span style={{ flex: 1, textAlign: "left", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {m.piece_jointe_nom}
                          </span>
                          <span style={{ fontSize: 11, opacity: 0.8 }}>
                            {formatTaille(m.piece_jointe_taille_octets ?? 0)}
                          </span>
                          <Download size={13} />
                        </button>
                      )}
                      <div style={{ fontSize: 11, opacity: 0.75, marginTop: 2 }}>
                        {new Date(m.date_envoi).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                {messages.length === 0 && <div className="empty-state">Aucun message</div>}
              </div>
              <form onSubmit={handleSend} style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <input
                  style={{ flex: 1 }}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Écrire un message..."
                />
                <input ref={fileInputRef} type="file" onChange={handleFileChange} style={{ display: "none" }} />
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={sending}
                  title={`Joindre un fichier (max ${tailleMaxMo} Mo)`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Paperclip size={16} />
                </button>
                <button className="btn btn-primary" disabled={sending || !input.trim()} type="submit">
                  Envoyer
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
