"""WebSocket endpoints.

``/ws/jobs/{user_id}``
    Receives :class:`material_update` events whenever a material changes
    status during background processing.  Identified by **user_id** so any
    number of browser tabs can subscribe.

Authentication
--------------
The browser cannot send custom headers on a WebSocket upgrade request, so the
JWT access-token is passed as a ``token`` query parameter:

    ws://host/ws/jobs/<user_id>?token=<jwt>

The endpoint verifies the token, confirms the caller's identity matches the
path parameter, then hands the socket to :data:`ws_manager`.

Message schema
--------------
All messages are JSON objects with a mandatory ``type`` discriminator:

.. code-block:: json

    {"type": "material_update", "material_id": "...", "status": "completed"}
    {"type": "ping"}            (keepalive sent every 30 s by the server)
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


# ── Auth helper ───────────────────────────────────────────────────────────


async def _authenticate(token: str) -> str | None:
    """Validate a JWT *token* and return the user_id string, or None."""
    if not token:
        return None
    try:
        from app.services.auth.security import decode_token
        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        return str(user_id) if user_id else None
    except Exception as exc:
        logger.debug("WS token validation failed: %s", exc)
        return None


def _close_msg(code: int, reason: str) -> None:
    """Return a pre-serialised close error message (send before closing)."""
    return json.dumps({"type": "error", "code": code, "reason": reason})


# ── /ws/jobs/{user_id} ────────────────────────────────────────────────────


@router.websocket("/ws/jobs/{user_id}")
async def ws_jobs(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(default=""),
):
    """WebSocket channel for material-processing job updates.

    The caller must be the owner of *user_id* (or an admin).
    Events pushed on this channel:

    .. code-block:: json

        {
            "type": "material_update",
            "material_id": "<uuid>",
            "status": "processing|ocr_running|transcribing|embedding|completed|failed",
            "error": "<msg>"   // only when status == "failed"
        }
    """
    # Authenticate
    caller_id = await _authenticate(token)
    if caller_id is None:
        await websocket.accept()
        await websocket.send_text(_close_msg(4001, "Unauthorized: invalid or missing token"))
        await websocket.close(code=4001)
        return

    if caller_id != user_id:
        await websocket.accept()
        await websocket.send_text(_close_msg(4003, "Forbidden: token user_id mismatch"))
        await websocket.close(code=4003)
        return

    await ws_manager.connect_user(user_id, websocket)
    logger.info("WS /ws/jobs/%s connected", user_id)

    # Send initial handshake
    await websocket.send_text(json.dumps({
        "type": "connected",
        "channel": "jobs",
        "user_id": user_id,
    }))

    try:
        # Keepalive + receive loop — the client can disconnect at any time.
        # We send a "ping" every 30 s to keep the TCP connection alive through
        # proxies/load-balancers with idle connection timeouts.
        _PING_INTERVAL = 30  # seconds
        while True:
            try:
                # Wait for either a client message or ping timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_PING_INTERVAL,
                )
                msg = json.loads(data)
                # Echo pong for client-initiated pings
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except asyncio.TimeoutError:
                # Send server-side keepalive ping
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                else:
                    break

    except WebSocketDisconnect:
        logger.info("WS /ws/jobs/%s disconnected", user_id)
    except Exception as exc:
        logger.warning("WS /ws/jobs/%s error: %s", user_id, exc)
    finally:
        ws_manager.disconnect_user(user_id, websocket)



