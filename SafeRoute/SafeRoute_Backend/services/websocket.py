"""
ai/services/websocket.py
=========================
Shared WebSocket connection manager for real-time SOS broadcasting.

Used by:
  - ai/main.py  (imported as admin_manager)
  - ai/api/routes/sos.py  (WebSocket /sos/stream endpoint)

Extracted from ai/main.py so downstream modules don't need to import
the entire monolith.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class AdminConnectionManager:
    """Manages all active admin WebSocket connections for real-time SOS broadcasting."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "Admin WS connected. Total admins online: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        try:
            self.active_connections.remove(websocket)
            logger.info(
                "Admin WS disconnected. Total admins online: %d",
                len(self.active_connections),
            )
        except ValueError:
            pass

    async def broadcast(self, message: dict) -> None:
        """Push a JSON message to every connected admin client simultaneously."""
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            try:
                self.active_connections.remove(d)
            except ValueError:
                pass

    def __len__(self) -> int:
        return len(self.active_connections)


# Global singleton — import this wherever WS broadcasting is needed
admin_manager = AdminConnectionManager()
