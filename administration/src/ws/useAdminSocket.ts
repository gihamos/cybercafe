import { useEffect, useRef, useState } from "react";
import { getToken, WS_BASE_URL } from "../api/client";

export interface AdminSocketMessage {
  type: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

const RECONNECT_DELAY_MS = 2000;

/** Connexion WebSocket vers /ws/admin, reconnexion automatique. Le callback est
 * appelé pour chaque message reçu (ex: "poste_updated") — voir router/ws_admin.py
 * et websocket/manager.py côté serveur. */
export function useAdminSocket(onMessage: (msg: AdminSocketMessage) => void) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    function connect() {
      ws = new WebSocket(`${WS_BASE_URL}/ws/admin?token=${encodeURIComponent(token!)}`);

      ws.onopen = () => setConnected(true);

      ws.onclose = () => {
        setConnected(false);
        if (!stopped) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };

      ws.onerror = () => ws?.close();

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          onMessageRef.current(msg);
        } catch {
          // message non-JSON, ignoré
        }
      };
    }

    connect();

    return () => {
      stopped = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return { connected };
}
