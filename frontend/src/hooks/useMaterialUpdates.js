import { useEffect, useRef, useCallback } from 'react';
import { apiConfig, getAccessToken } from '../api/config';

/**
 * React hook that connects to the backend WebSocket for real-time
 * material processing updates.
 *
 * @param {string|null} userId  – current user's ID (skip if null)
 * @param {(msg: object) => void} onMessage – handler for incoming messages
 * @returns {{ connected: boolean }}
 */
export function useMaterialUpdates(userId, onMessage) {
  const wsRef = useRef(null);
  const connectedRef = useRef(false);
  const reconnectTimer = useRef(null);
  const onMessageRef = useRef(onMessage);

  // Keep callback ref current without triggering reconnect
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (!userId) return;

    const token = getAccessToken();
    if (!token) return;

    // Derive WS URL from API base (http→ws, https→wss)
    const base = apiConfig.baseUrl.replace(/^http/, 'ws');
    const url = `${base}/ws/jobs/${userId}?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        connectedRef.current = true;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          // Handle keepalive internally
          if (msg.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }
          if (msg.type === 'connected') return;

          // Forward all other messages to consumer
          onMessageRef.current?.(msg);
        } catch (err) {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        connectedRef.current = false;
        wsRef.current = null;
        // Auto-reconnect after 5s (unless unmounted)
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        // onclose will fire after onerror
      };

      wsRef.current = ws;
    } catch {
      // WebSocket constructor can throw if URL is malformed
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [userId]);

  useEffect(() => {
    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
      connectedRef.current = false;
    };
  }, [connect]);

  return { connected: connectedRef.current };
}
