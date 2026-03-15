"""
ai/core/config.py
==================
Unified configuration for the SafeRoute AI backend.
Re-exports everything from safety_config.py and adds new constants
needed by the modular service layer.

IMPORTANT: safety_config.py is NOT replaced — ai/main.py still imports from it.
This module is the canonical config for all new ai/services/ and ai/api/ modules.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the ai/ directory
_AI_DIR = Path(__file__).parent.parent
load_dotenv(_AI_DIR / ".env")

# ---------------------------------------------------------------------------
# Directory references
# ---------------------------------------------------------------------------
BASE_DIR = _AI_DIR / "data"  # ai/

# ---------------------------------------------------------------------------
# Re-export everything from the original safety_config so that new modules
# can use a single import: `from core.config import WEIGHTS, BOUNDS, ...`
# ---------------------------------------------------------------------------
from core.safety_config import (  # noqa: E402  (must come after load_dotenv)
    API_KEY,
    BOUNDS,
    WEIGHTS,
    MAX_VALUES,
    GACHIBOWLI_CENTER,
    COVERAGE_RADIUS_METERS,
    JUNCTION_CONFIG,
    coords_in_bounds,
    get_time_multiplier,
    haversine_distance,
    is_within_radius,
    get_coverage_info,
    format_coordinate_debug,
)

# ---------------------------------------------------------------------------
# Database paths — single source of truth
# ---------------------------------------------------------------------------
GRID_FILE: Path = BASE_DIR / "data1.json"
SOS_DB_PATH: Path = BASE_DIR / "sos_alerts.db"
SAFE_ROUTES_DB_PATH: Path = BASE_DIR / "safe_routes.db"

def _resolve_database_url() -> str:
    """
    Normalize SQLite URLs so relative paths resolve from the backend directory.

    This avoids drift between `SafeRoute_Backend/safe_routes.db` and
    `SafeRoute_Backend/data/safe_routes.db`.
    """
    raw = os.getenv("DATABASE_URL")
    if not raw:
        return f"sqlite:///{SAFE_ROUTES_DB_PATH.resolve()}"

    if raw.startswith("sqlite:///"):
        sqlite_target = raw.removeprefix("sqlite:///")
        sqlite_path = Path(sqlite_target)
        if not sqlite_path.is_absolute():
            sqlite_path = (_AI_DIR / sqlite_path).resolve()
        if sqlite_path.name == "safe_routes.db" and sqlite_path.parent == _AI_DIR:
            sqlite_path = SAFE_ROUTES_DB_PATH.resolve()
        return f"sqlite:///{sqlite_path}"

    return raw


# SQLAlchemy-compatible URL for the familiarity module
DATABASE_URL: str = _resolve_database_url()

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def _parse_csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", API_KEY)
ENFORCE_ADMIN_API_KEY: bool = os.getenv("ENFORCE_ADMIN_API_KEY", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CORS_ALLOWED_ORIGINS: list[str] = _parse_csv_env(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:19006,http://127.0.0.1:19006",
)
CORS_ALLOWED_ORIGIN_REGEX: str = os.getenv(
    "CORS_ALLOWED_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?$",
)

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
ROUTE_GRAPH_CACHE_TTL_SECONDS: int = int(
    os.getenv("ROUTE_GRAPH_CACHE_TTL_SECONDS", str(max(CACHE_TTL_SECONDS, 900)))
)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
ROUTE_RATE_LIMIT_REQUESTS: int = int(os.getenv("ROUTE_RATE_LIMIT_REQUESTS", "60"))
ROUTE_RATE_LIMIT_WINDOW_SECONDS: int = int(
    os.getenv("ROUTE_RATE_LIMIT_WINDOW_SECONDS", "60")
)
SOS_RATE_LIMIT_REQUESTS: int = int(os.getenv("SOS_RATE_LIMIT_REQUESTS", "10"))
SOS_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("SOS_RATE_LIMIT_WINDOW_SECONDS", "60"))
CRIME_RATE_LIMIT_REQUESTS: int = int(os.getenv("CRIME_RATE_LIMIT_REQUESTS", "20"))
CRIME_RATE_LIMIT_WINDOW_SECONDS: int = int(
    os.getenv("CRIME_RATE_LIMIT_WINDOW_SECONDS", "60")
)
ADMIN_READ_RATE_LIMIT_REQUESTS: int = int(
    os.getenv("ADMIN_READ_RATE_LIMIT_REQUESTS", "120")
)
ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS: int = int(
    os.getenv("ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS", "60")
)

# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------
HEATMAP_GRID_SIZE: int = 20
HEATMAP_POINT_RADIUS_M: int = 150
HEATMAP_MIN_WEIGHT: float = 0.15
