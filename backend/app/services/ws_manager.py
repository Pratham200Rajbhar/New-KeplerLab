"""WebSocket connection manager — process-level singleton.

Tracks live WebSocket connections keyed by:
  • user_id   — for material-processing job updates  (/ws/jobs/{user_id})

Multiple browser tabs or reconnects for the same key are supported; each
produces an independent WebSocket entry in the relevant list.

Usage (backend services)::

    from app.services.ws_manager import ws_manager

    # User-scoped events (material processing)
    await ws_manager.send_to_user(user_id, {"type": "material_update", ...})

    # Broadcast to all connections (e.g. system alerts — rarely needed)
    await ws_manager.broadcast({"type": "ping"})
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe WebSocket connection registry.

    CPython GIL + asyncio single-threaded event loop mean ordinary dicts are
    safe here; no extra locking is required.
    """

    MAX_CONNECTIONS_PER_USER = 10  # Prevent DoS via excessive WS connections

    def __init__(self) -> None:
        # user_id  → list of active WebSocket objects
        self._user_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    # ── Connection lifecycle ───────────────────────────────────────

    async def connect_user(self, user_id: str, ws: WebSocket) -> None:
        """Accept and register a user-scoped WebSocket.
        
        Rejects connections exceeding MAX_CONNECTIONS_PER_USER.
        """
        current_count = len(self._user_connections.get(user_id, []))
        if current_count >= self.MAX_CONNECTIONS_PER_USER:
            await ws.accept()
            await ws.send_text('{"type":"error","reason":"Too many connections"}')
            await ws.close(code=4008)
            logger.warning(
                "WS rejected: user=%s exceeded max connections (%d)",
                user_id, self.MAX_CONNECTIONS_PER_USER,
            )
            return
        await ws.accept()
        self._user_connections[user_id].append(ws)
        logger.info(
            "WS connect: user=%s  total_user_conns=%d",
            user_id, len(self._user_connections[user_id]),
        )

    def disconnect_user(self, user_id: str, ws: WebSocket) -> None:
        """Remove a user-scoped WebSocket (call on close or error)."""
        conns = self._user_connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._user_connections.pop(user_id, None)
        logger.info(
            "WS disconnect: user=%s  remaining=%d",
            user_id, len(self._user_connections.get(user_id, [])),
        )



    # ── Sending helpers ────────────────────────────────────────────

    async def send_to_user(self, user_id: str, payload: Dict[str, Any]) -> int:
        """Push a JSON payload to every WebSocket registered for *user_id*.

        Returns the number of connections that received the message.
        Dead connections are pruned automatically.
        """
        return await self._send_to_connections(
            self._user_connections.get(user_id, []),
            payload,
            prune_key=("user", user_id),
        )



    async def broadcast(self, payload: Dict[str, Any]) -> int:
        """Send *payload* to every active user connection.

        Returns the total number of successful sends.
        """
        text = json.dumps(payload)
        total = 0
        for uid, conns in list(self._user_connections.items()):
            for ws in list(conns):
                try:
                    await ws.send_text(text)
                    total += 1
                except Exception:
                    self.disconnect_user(uid, ws)
        return total

    # ── Presence queries ───────────────────────────────────────────

    def user_is_connected(self, user_id: str) -> bool:
        return bool(self._user_connections.get(user_id))

    def stats(self) -> Dict[str, int]:
        return {
            "user_connections": sum(len(v) for v in self._user_connections.values()),
            "unique_users": len(self._user_connections),
        }

    # ── Internal ───────────────────────────────────────────────────

    async def _send_to_connections(
        self,
        conns: List[WebSocket],
        payload: Dict[str, Any],
        prune_key: tuple,
    ) -> int:
        """Send serialised payload to a list of WebSocket objects.

        Dead sockets are removed from the registry.
        """
        if not conns:
            return 0

        text = json.dumps(payload)
        sent = 0
        dead: List[WebSocket] = []

        for ws in list(conns):
            try:
                await ws.send_text(text)
                sent += 1
            except Exception as exc:
                logger.debug(
                    "WS send failed (%s=%s): %s — pruning connection",
                    prune_key[0], prune_key[1], exc,
                )
                dead.append(ws)

        # Prune dead connections
        for ws in dead:
            scope, key = prune_key
            if scope == "user":
                self.disconnect_user(key, ws)

        return sent


# ── Process-level singleton ────────────────────────────────────────────────
ws_manager = ConnectionManager()
