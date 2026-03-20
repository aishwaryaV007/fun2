from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import logging

from services.sos_service import trigger_and_broadcast, list_sos_alerts, resolve_sos_alert
from services.websocket import admin_manager

router = APIRouter(prefix="/sos", tags=["SOS"])
logger = logging.getLogger(__name__)

from typing import Optional, Any

class SOSAlertPayload(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    timestamp: str
    message: Optional[str] = None
    device_info: Optional[str] = None
    trigger_type: Optional[str] = None
    device_ip: Optional[str] = None

@router.post("/trigger")
@router.post("")
async def trigger_sos(payload: SOSAlertPayload):
    """Trigger an emergency SOS alert and broadcast it directly to admins."""
    try:
        kwargs: dict[str, Any] = {
            "user_id": payload.user_id,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "timestamp": payload.timestamp,
        }
        if payload.message is not None:
            kwargs["message"] = payload.message
        if payload.device_info is not None:
            kwargs["device_info"] = payload.device_info
        if payload.trigger_type is not None:
            kwargs["trigger_type"] = payload.trigger_type
        if payload.device_ip is not None:
            kwargs["device_ip"] = payload.device_ip

        result = await trigger_and_broadcast(**kwargs)
        return result
    except Exception as e:
        logger.error(f"Failed to trigger SOS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """Fetch the most recent SOS alerts."""
    return list_sos_alerts(limit)

@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Mark an active SOS alert as resolved."""
    success = resolve_sos_alert(alert_id, "resolved")
    if not success:
        raise HTTPException(status_code=404, detail="SOS Alert not found or could not be updated.")
    return {"status": "resolved", "alert_id": alert_id}

@router.websocket("/stream")
async def sos_stream(websocket: WebSocket):
    """Global WebSocket stream for Admin Dashboard to listen to live SOS alerts."""
    await admin_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        admin_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        admin_manager.disconnect(websocket)
