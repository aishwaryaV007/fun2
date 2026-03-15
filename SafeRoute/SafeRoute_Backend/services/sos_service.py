"""
ai/services/sos_service.py
===========================
SOS alert service layer for the SafeRoute AI backend.

Provides:
  - Database initialisation (CREATE TABLE IF NOT EXISTS + safe migrations)
  - Persist an incoming SOS alert (with message, device_ip, trigger_type)
  - List recent SOS alerts
  - Duplicate detection + per-user rate limiting
  - Full trigger-and-broadcast pipeline

Both ai/main.py and the API route modules (ai/api/routes/sos.py) use this
service so there is no duplicated SQL anywhere.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import SOS_DB_PATH
from services.websocket import admin_manager  # shared singleton

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate-limit + duplicate protection
# ---------------------------------------------------------------------------
# Maps user_id → last trigger epoch seconds.
# If a new trigger arrives from the same user within COOLDOWN_SECONDS AND
# within DUPLICATE_RADIUS_DEG degrees of the last location, it is rejected.

_user_last_trigger: dict[str, tuple[float, float, float]] = {}
# {user_id: (last_epoch, last_lat, last_lng)}

COOLDOWN_SECONDS:    float = 5.0    # minimum gap between alerts per user
DUPLICATE_RADIUS_DEG: float = 0.001  # ~110 m — treat same spot as duplicate


def _is_rate_limited(user_id: str, lat: float, lng: float) -> bool:
    """
    Return True (and log a warning) if this alert should be suppressed.

    An alert is suppressed when BOTH:
      - less than COOLDOWN_SECONDS have passed since the user's last alert, AND
      - the new location is within DUPLICATE_RADIUS_DEG of the last location.
    """
    now = time.time()
    entry = _user_last_trigger.get(user_id)
    if entry:
        last_t, last_lat, last_lng = entry
        age = now - last_t
        dist = ((lat - last_lat) ** 2 + (lng - last_lng) ** 2) ** 0.5
        if age < COOLDOWN_SECONDS and dist < DUPLICATE_RADIUS_DEG:
            logger.warning(
                "SOS rate-limited for user=%s — %.1f s since last alert (min %.1f s), "
                "distance=%.5f deg (min %.5f deg)",
                user_id, age, COOLDOWN_SECONDS, dist, DUPLICATE_RADIUS_DEG,
            )
            return True
    _user_last_trigger[user_id] = (now, lat, lng)
    return False


# ---------------------------------------------------------------------------
# Internal DB helper
# ---------------------------------------------------------------------------

def _get_sos_db() -> sqlite3.Connection:
    conn = sqlite3.connect(SOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _create_index(conn: sqlite3.Connection, name: str, ddl: str) -> None:
    conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {ddl}")


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def init_sos_db() -> None:
    """
    Create the sos_alerts table if it does not already exist, and
    safely add any new columns to existing databases via ALTER TABLE.

    Called once at application startup.
    """
    conn = _get_sos_db()

    # Create base table (v1 schema)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT    NOT NULL,
            latitude    REAL    NOT NULL,
            longitude   REAL    NOT NULL,
            timestamp   TEXT    NOT NULL,
            received_at TEXT    DEFAULT (datetime('now')),
            device_info TEXT    DEFAULT 'Unknown Device',
            status      TEXT    DEFAULT 'active'
        )
    """)

    # Safe migrations — add new columns if they don't exist yet
    _safe_add_column(conn, "sos_alerts", "device_info",  "TEXT DEFAULT 'Unknown Device'")
    _safe_add_column(conn, "sos_alerts", "status",       "TEXT DEFAULT 'active'")
    _safe_add_column(conn, "sos_alerts", "message",      "TEXT DEFAULT 'SOS Alert'")
    _safe_add_column(conn, "sos_alerts", "device_ip",    "TEXT DEFAULT 'Unknown'")
    _safe_add_column(conn, "sos_alerts", "trigger_type", "TEXT DEFAULT 'button'")
    _safe_add_column(conn, "sos_alerts", "delayed",      "INTEGER DEFAULT 0")  # 1 = delayed
    _create_index(conn, "idx_sos_alerts_user_id", "sos_alerts (user_id)")
    _create_index(conn, "idx_sos_alerts_status", "sos_alerts (status)")
    _create_index(conn, "idx_sos_alerts_timestamp", "sos_alerts (timestamp)")
    _create_index(conn, "idx_sos_alerts_status_date", "sos_alerts (status, date(timestamp))")
    _create_index(conn, "idx_sos_alerts_lat_lng", "sos_alerts (latitude, longitude)")

    conn.commit()
    conn.close()
    logger.info("SOS alerts table ready (with migrations) at %s", SOS_DB_PATH)


def _safe_add_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to `table` if it doesn't exist. Silently skips if already present."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        logger.info("Migrated DB: added column '%s' to '%s'", column, table)
    except sqlite3.OperationalError:
        pass  # Column already exists — expected on subsequent startups


def persist_sos_alert(
    user_id: str,
    latitude: float,
    longitude: float,
    timestamp: str,
    device_info: str = "Unknown Device",
    message: str = "SOS Alert",
    device_ip: str = "Unknown",
    trigger_type: str = "button",
    delayed: bool = False,
) -> int:
    """Insert an SOS alert into the database and return its new row ID."""
    conn = _get_sos_db()
    cursor = conn.execute(
        """INSERT INTO sos_alerts
               (user_id, latitude, longitude, timestamp, device_info,
                message, device_ip, trigger_type, delayed)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, latitude, longitude, timestamp, device_info,
         message, device_ip, trigger_type, 1 if delayed else 0),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.warning(
        "SOS ALERT persisted — user=%s  (%.6f, %.6f)  trigger=%s  device=%s  ip=%s  delayed=%s",
        user_id, latitude, longitude, trigger_type, device_info, device_ip, delayed,
    )
    return row_id


def list_sos_alerts(limit: int = 50) -> list[dict]:
    """Return the most recent SOS alerts as a list of dicts."""
    conn = _get_sos_db()
    rows = conn.execute(
        """SELECT id, user_id, latitude, longitude, timestamp, received_at,
                  device_info, status, message, device_ip, trigger_type, delayed
           FROM sos_alerts
           ORDER BY id DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id":           r["id"],
            "user_id":      r["user_id"],
            "latitude":     r["latitude"],
            "longitude":    r["longitude"],
            "timestamp":    r["timestamp"],
            "received_at":  r["received_at"],
            "alert_type":   "SOS",
            "device_info":  r["device_info"]  or "Unknown Device",
            "status":       r["status"]        or "active",
            "message":      r["message"]       or "SOS Alert",
            "device_ip":    r["device_ip"]     or "Unknown",
            "trigger_type": r["trigger_type"]  or "button",
            "delayed":      bool(r["delayed"]) if r["delayed"] is not None else False,
        }
        for r in rows
    ]


def resolve_sos_alert(alert_id: int, status: str) -> bool:
    """Update the status column of an SOS alert. Returns True if a row was updated."""
    conn = _get_sos_db()
    try:
        cursor = conn.execute(
            "UPDATE sos_alerts SET status = ? WHERE id = ?",
            (status, alert_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.OperationalError:
        logger.warning("Could not update status on sos_alerts — column may be absent.")
        return False
    finally:
        conn.close()


async def trigger_and_broadcast(
    user_id: str,
    latitude: float,
    longitude: float,
    timestamp: str,
    device_info: str = "Unknown Device",
    message: str = "SOS Alert",
    device_ip: str = "Unknown",
    trigger_type: str = "button",
    delayed: bool = False,
) -> dict:
    """
    Full SOS pipeline:
      1. Rate-limit / duplicate check
      2. Persist to SQLite
      3. Build broadcast payload
      4. Broadcast to all connected admin WebSocket clients
      5. Return result dict

    Returns:
        dict with "status", "admin_clients_notified", and optionally "skipped" flag.
    """
    # ── Safety check ──────────────────────────────────────────────────────
    if _is_rate_limited(user_id, latitude, longitude):
        return {
            "status": "duplicate SOS suppressed",
            "skipped": True,
            "admin_clients_notified": 0,
            "reason": (
                f"Alert from user '{user_id}' suppressed: "
                f"duplicate trigger within {COOLDOWN_SECONDS}s cooldown window."
            ),
        }

    # ── Persist ────────────────────────────────────────────────────────────
    alert_id = persist_sos_alert(
        user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        device_info=device_info,
        message=message,
        device_ip=device_ip,
        trigger_type=trigger_type,
        delayed=delayed,
    )

    # ── Broadcast ──────────────────────────────────────────────────────────
    payload = {
        "id":           alert_id,
        "type":         "SOS_ALERT",
        "alert_type":   "SOS",
        "user_id":      user_id,
        "location": {
            "lat": latitude,
            "lng": longitude,
        },
        # Flat fields for backward compatibility with clients reading .latitude/.longitude
        "latitude":     latitude,
        "longitude":    longitude,
        "message":      message,
        "trigger_type": trigger_type,
        "device_ip":    device_ip,
        "device_info":  device_info,
        "timestamp":    timestamp,
        "received_at":  datetime.utcnow().isoformat() + "Z",
        "delayed":      delayed,
    }

    await admin_manager.broadcast(payload)

    return {
        "alert_id": alert_id,
        "status": "SOS alert received and broadcasted",
        "skipped": False,
        "admin_clients_notified": len(admin_manager.active_connections),
        "delayed": delayed,
    }
