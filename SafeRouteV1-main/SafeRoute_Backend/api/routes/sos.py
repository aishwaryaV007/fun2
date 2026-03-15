"""
ai/api/routes/sos.py
=====================
Canonical SOS endpoints for the unified SafeRoute AI backend.

Exposes:
  POST /sos/trigger    — submit an SOS alert (persists + broadcasts)
  GET  /sos/alerts     — list recent SOS alerts
  WS   /sos/stream     — WebSocket alias for /ws/admin_alert
  POST /sos/{id}/resolve — mark an alert resolved

Legacy endpoints on ai/main.py (/sos_alert, /sos_alerts, /ws/admin_alert)
remain active for backward compatibility.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from core.config import (
    ADMIN_READ_RATE_LIMIT_REQUESTS,
    ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    BOUNDS,
    SOS_RATE_LIMIT_REQUESTS,
    SOS_RATE_LIMIT_WINDOW_SECONDS,
    coords_in_bounds,
)
from core.security import (
    require_admin_api_key_if_enabled,
    require_websocket_admin_api_key_if_enabled,
)
from services.rate_limiter import enforce_rate_limit
from services.sos_service import (
    trigger_and_broadcast,
    list_sos_alerts,
    resolve_sos_alert,
)
from services.websocket import admin_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sos", tags=["SOS"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SOSTriggerRequest(BaseModel):
    """
    Full SOS alert payload.

    All fields except user_id/lat/lng/timestamp are optional so the endpoint
    stays backward-compatible with the old /sos_alert schema.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_id:      str = Field(min_length=1, max_length=128)
    latitude:     float = Field(ge=-90, le=90)
    longitude:    float = Field(ge=-180, le=180)
    timestamp:    str = Field(min_length=4, max_length=64)        # ISO 8601

    # ── New enrichment fields ──────────────────────────────────────────────
    message:      Optional[str]  = Field(
        default="SOS Alert",
        max_length=500,
        description="Human-readable description of why the SOS was triggered.",
    )
    device_ip:    Optional[str]  = Field(
        default="Unknown",
        max_length=64,
        description="IP address of the triggering device.",
    )
    trigger_type: Optional[str]  = Field(
        default="button",
        max_length=32,
        description='How the SOS was triggered: "button" or "shake".',
    )
    # ── Legacy field (kept for backward compat) ────────────────────────────
    device_info:  Optional[str]  = Field(
        default="Unknown Mobile Device",
        max_length=256,
        description="Device model / OS string.",
    )
    # ── Offline delivery flag ──────────────────────────────────────────────
    delayed:      Optional[bool] = Field(
        default=False,
        description="True when the alert was cached offline and delivered later.",
    )


class SOSResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["resolved", "false_alarm", "reviewed"] = "resolved"


# ---------------------------------------------------------------------------
# POST /sos/trigger
# ---------------------------------------------------------------------------

@router.post(
    "/trigger",
    summary="Submit an SOS alert",
    response_description="Status of the alert including how many admins were notified",
)
async def trigger_sos(alert: SOSTriggerRequest, request: Request):
    """
    Canonical SOS alert endpoint.

    Pipeline:
      1. Rate-limit / duplicate check (5-second per-user cooldown)
      2. Persist alert to SQLite (sos_alerts.db)
      3. Broadcast real-time payload to all admin WebSocket clients
      4. Return result with skipped flag + notified count

    Example payload:
    ```json
    {
      "user_id": "user-123",
      "latitude": 17.43,
      "longitude": 78.34,
      "message": "SOS triggered with the shake of phone",
      "device_ip": "192.168.0.10",
      "trigger_type": "shake",
      "timestamp": "2026-03-06T22:00:00Z"
    }
    ```
    """
    enforce_rate_limit(
        request,
        scope="sos.trigger",
        limit=SOS_RATE_LIMIT_REQUESTS,
        window_seconds=SOS_RATE_LIMIT_WINDOW_SECONDS,
        subject=alert.user_id,
    )

    if not coords_in_bounds(alert.latitude, alert.longitude):
        raise HTTPException(
            status_code=400,
            detail=(
                "SOS coordinates are outside the supported area. "
                f"Bounds: lat [{BOUNDS['min_lat']}, {BOUNDS['max_lat']}], "
                f"lng [{BOUNDS['min_lng']}, {BOUNDS['max_lng']}]"
            ),
        )

    return await trigger_and_broadcast(
        user_id=alert.user_id,
        latitude=alert.latitude,
        longitude=alert.longitude,
        timestamp=alert.timestamp,
        device_info=alert.device_info  or "Unknown Mobile Device",
        message=alert.message          or "SOS Alert",
        device_ip=alert.device_ip      or "Unknown",
        trigger_type=alert.trigger_type or "button",
        delayed=alert.delayed          or False,
    )


# ---------------------------------------------------------------------------
# GET /sos/alerts
# ---------------------------------------------------------------------------

@router.get(
    "/alerts",
    summary="List recent SOS alerts",
    response_description="List of SOS alerts ordered by newest first",
)
async def get_sos_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    _: str | None = Depends(require_admin_api_key_if_enabled),
):
    """
    Returns the most recent SOS alerts from the database (newest first).
    Each alert includes: id, user_id, latitude, longitude, timestamp,
    message, trigger_type, device_ip, device_info, status.
    """
    enforce_rate_limit(
        request,
        scope="sos.alerts",
        limit=ADMIN_READ_RATE_LIMIT_REQUESTS,
        window_seconds=ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    )
    return list_sos_alerts(limit=limit)


# ---------------------------------------------------------------------------
# POST /sos/{alert_id}/resolve
# ---------------------------------------------------------------------------

@router.post(
    "/{alert_id}/resolve",
    summary="Resolve an SOS alert",
)
async def resolve_alert(
    alert_id: int = Path(gt=0),
    body: SOSResolveRequest = ...,
    _: str | None = Depends(require_admin_api_key_if_enabled),
):
    """Mark an SOS alert as resolved / false alarm / reviewed."""
    updated = resolve_sos_alert(alert_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"alert_id": alert_id, "status": body.status}


# ---------------------------------------------------------------------------
# WebSocket /sos/stream
# ---------------------------------------------------------------------------

@router.websocket("/stream")
async def sos_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time SOS push notifications.
    Canonical alias for WS /ws/admin_alert.

    Admin dashboard connects here and receives all SOS alerts in real-time
    as they are submitted via POST /sos/trigger or POST /sos_alert.
    Multiple admin clients can connect simultaneously.

    Payload format:
    ```json
    {
      "type": "SOS_ALERT",
      "user_id": "...",
      "location": { "lat": ..., "lng": ... },
      "message": "...",
      "trigger_type": "shake",
      "device_ip": "...",
      "timestamp": "...",
      "received_at": "..."
    }
    ```
    """
    require_websocket_admin_api_key_if_enabled(websocket)
    await admin_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; admin receives pushes but rarely sends.
            # Any message from admin (e.g. ping) is ignored gracefully.
            await websocket.receive_text()
    except WebSocketDisconnect:
        admin_manager.disconnect(websocket)
    except Exception as e:
        logger.error("SOS stream WebSocket error: %s", e)
        admin_manager.disconnect(websocket)
