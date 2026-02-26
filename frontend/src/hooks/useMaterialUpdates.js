import { useEffect, useRef, useCallback, useState } from 'react';
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
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef(null);
  const reconnectAttempts = useRef(0);
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
    // Don't put token in URL (leaks to server logs, browser history, proxies)
    // Send it as the first message after connection instead
    const url = `${base}/ws/jobs/${userId}`;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        // Authenticate via first message instead of query param
        ws.send(JSON.stringify({ type: 'auth', token }));
        setConnected(true);
        reconnectAttempts.current = 0; // Reset on successful connect
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
        setConnected(false);
        wsRef.current = null;
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        // onclose will fire after onerror
      };

      wsRef.current = ws;
    } catch {
      // WebSocket constructor can throw if URL is malformed
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current += 1;
      reconnectTimer.current = setTimeout(connect, delay);
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
      setConnected(false);
    };
  }, [connect]);

  return { connected };
}
