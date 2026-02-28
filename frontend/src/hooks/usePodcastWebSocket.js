import { useEffect, useRef } from 'react';
import { usePodcast } from '../context/PodcastContext';

/**
 * Hooks into the existing WebSocket connection and listens for
 * podcast-specific events, routing them into PodcastContext.
 *
 * Expects that the page already has a WS connection
 * (managed elsewhere in the app).  This hook registers a
 * `message` listener with the standard podcast event types.
 */
export default function usePodcastWebSocket(wsRef) {
  const { handleWsEvent } = usePodcast();
  const handlerRef = useRef(handleWsEvent);
  handlerRef.current = handleWsEvent;

  useEffect(() => {
    const ws = wsRef?.current;
    if (!ws) return;

    const onMessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type && msg.type.startsWith('podcast_')) {
          handlerRef.current(msg);
        }
      } catch {
        // Not JSON or not a podcast event — ignore
      }
    };

    ws.addEventListener('message', onMessage);
    return () => ws.removeEventListener('message', onMessage);
  }, [wsRef]);
}
