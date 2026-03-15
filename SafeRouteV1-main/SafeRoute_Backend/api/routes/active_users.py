"""
api/routes/active_users.py
===========================
Real-time active users tracking via WebSocket heartbeat.

Exposes:
  WS  /ws/users    — mobile device connects here; heartbeat keeps it alive
  GET /users/count — REST fallback to get current active user count
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from core.config import ADMIN_READ_RATE_LIMIT_REQUESTS, ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS
from core.security import require_admin_api_key_if_enabled
from services.rate_limiter import enforce_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Active Users"])

# -------------------------------------------------------------------------
# In-memory registry: ws_id → last_seen timestamp
# -------------------------------------------------------------------------
_active_users: dict[int, str] = {}   # id(websocket) → iso timestamp
_user_sockets: list[WebSocket] = []  # all open mobile WS connections

# admin connections that want active_users updates
_admin_subscribers: list[WebSocket] = []


async def _broadcast_count() -> None:
    """Push the current active-users count to every subscribed admin."""
    from services.websocket import admin_manager  # avoid circular at module level
    payload = {
        "type": "active_users",
        "count": len(_active_users),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await admin_manager.broadcast(payload)
    logger.info("Active users broadcast: count=%d", len(_active_users))


# -------------------------------------------------------------------------
# WebSocket endpoint — one connection per mobile device
# -------------------------------------------------------------------------

@router.websocket("/ws/users")
async def mobile_heartbeat(websocket: WebSocket):
    """
    Mobile app connects here to register as an active user.
    The client should send any message (e.g. "ping") every 30 seconds
    to prove it is still alive.  Disconnecting removes the user count.
    """
    await websocket.accept()
    uid = id(websocket)
    _active_users[uid] = datetime.utcnow().isoformat() + "Z"
    _user_sockets.append(websocket)
    logger.info("Mobile device connected — uid=%s  active=%d", uid, len(_active_users))
    await _broadcast_count()

    try:
        while True:
            # Wait for heartbeat message (any text/bytes)
            await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            _active_users[uid] = datetime.utcnow().isoformat() + "Z"
    except asyncio.TimeoutError:
        logger.warning("Mobile device timed out — uid=%s", uid)
    except WebSocketDisconnect:
        logger.info("Mobile device disconnected — uid=%s", uid)
    except Exception as exc:
        logger.error("Mobile WS error uid=%s: %s", uid, exc)
    finally:
        _active_users.pop(uid, None)
        try:
            _user_sockets.remove(websocket)
        except ValueError:
            pass
        logger.info("Removed uid=%s. Active users now: %d", uid, len(_active_users))
        await _broadcast_count()


# -------------------------------------------------------------------------
# REST fallback
# -------------------------------------------------------------------------

@router.get("/users/count")
async def get_active_users_count(
    request: Request,
    _: str | None = Depends(require_admin_api_key_if_enabled),
):
    """Returns the current number of connected mobile devices."""
    enforce_rate_limit(
        request,
        scope="users.count",
        limit=ADMIN_READ_RATE_LIMIT_REQUESTS,
        window_seconds=ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    )
    return {"active_users": len(_active_users), "timestamp": datetime.utcnow().isoformat() + "Z"}
