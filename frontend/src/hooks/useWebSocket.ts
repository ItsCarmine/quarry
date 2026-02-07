import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage } from "../types";

export function useWebSocket(reportId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [stage, setStage] = useState<string>("");
  const [typstSource, setTypstSource] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!reportId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/research/${reportId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      switch (msg.type) {
        case "status":
          setStage(msg.stage);
          break;
        case "report":
          setTypstSource(msg.typst_source);
          break;
        case "error":
          setError(msg.detail);
          break;
      }
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError("WebSocket connection failed");

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [reportId]);

  const send = useCallback((data: string) => {
    wsRef.current?.send(data);
  }, []);

  return { stage, typstSource, error, connected, send };
}
