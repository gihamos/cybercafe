import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { MessageCircle, Send } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { MessageChat } from "../api/types";

export default function ChatPage() {
  const [messages, setMessages] = useState<MessageChat[]>([]);
  const [texte, setTexte] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const finRef = useRef<HTMLDivElement | null>(null);
  const nbMessagesRef = useRef(0);

  const charger = useCallback(async () => {
    try {
      const data = await api.get<MessageChat[]>("/portail/chat");
      setMessages(data);
    } catch {
      /* silencieux : on retentera au prochain tick */
    }
  }, []);

  useEffect(() => {
    charger();
    const interval = setInterval(charger, 5000);
    return () => clearInterval(interval);
  }, [charger]);

  useEffect(() => {
    if (messages.length > nbMessagesRef.current) {
      finRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    nbMessagesRef.current = messages.length;
  }, [messages]);

  async function envoyer(e: FormEvent) {
    e.preventDefault();
    if (!texte.trim()) return;
    setError(null);
    setSending(true);
    try {
      const msg = await api.post<MessageChat>("/portail/chat", { message: texte.trim() });
      setMessages((prev) => [...prev, msg]);
      setTexte("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <div className="section-titre">
        <MessageCircle size={17} /> Discussion avec l'accueil
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
        <div className="chat-fil">
          {messages.length === 0 && (
            <div className="empty-state">
              Une question, un souci de connexion ? Écrivez-nous, l'équipe vous répond ici.
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`bulle ${m.expediteur === "client" ? "moi" : "eux"}`}>
              {m.message}
              <time>{new Date(m.date_envoi).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
            </div>
          ))}
          <div ref={finRef} />
        </div>

        {error && <p className="error">{error}</p>}

        <form onSubmit={envoyer} style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="Votre message..."
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            maxLength={2000}
          />
          <button className="btn btn-primary" type="submit" disabled={sending || !texte.trim()} style={{ flexShrink: 0 }}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </>
  );
}
