from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("stream_manager")


class StreamManager:
    """Manages WebSocket connections per session for real-time agent streaming."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._sessions.setdefault(session_id, []).append(ws)
        logger.info(f"WebSocket connected: session={session_id}")

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        sockets = self._sessions.get(session_id, [])
        if ws in sockets:
            sockets.remove(ws)
        if not self._sessions.get(session_id):
            self._sessions.pop(session_id, None)
        logger.info(f"WebSocket disconnected: session={session_id}")

    async def broadcast(self, session_id: str, event: dict[str, Any]) -> None:
        """Send a JSON event to all WebSocket clients for *session_id*."""
        sockets = self._sessions.get(session_id, [])
        if not sockets:
            return

        message = json.dumps(event, default=str)
        stale: list[WebSocket] = []

        for ws in sockets:
            try:
                await ws.send_text(message)
            except WebSocketDisconnect:
                stale.append(ws)
            except Exception:
                logger.exception(f"Failed to send to session {session_id}")
                stale.append(ws)

        # Clean up stale connections
        for ws in stale:
            await self.disconnect(session_id, ws)

    async def broadcast_nowait(self, session_id: str, event: dict[str, Any]) -> None:
        """Fire-and-forget broadcast — won't block the agent loop."""
        try:
            await self.broadcast(session_id, event)
        except Exception:
            pass

    def is_connected(self, session_id: str) -> bool:
        return bool(self._sessions.get(session_id))


# Global singleton
stream_manager = StreamManager()
