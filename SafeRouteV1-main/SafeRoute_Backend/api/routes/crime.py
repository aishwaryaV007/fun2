"""
ai/api/routes/crime.py
========================
Crime Reporting Flow Implementation

This module handles incoming crime reports, logs them into `crime_reports.db`,
and dynamically updates the nearest road segment's safety score in `safe_routes.db`.
"""

import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from core.config import (
    BOUNDS,
    CRIME_RATE_LIMIT_REQUESTS,
    CRIME_RATE_LIMIT_WINDOW_SECONDS,
    coords_in_bounds,
)
from services.rate_limiter import enforce_rate_limit

from services.incident_severity import calculate_new_safety_score

# Database Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CRIME_DB_PATH = BASE_DIR / "data" / "crime_reports.db"
SAFE_ROUTES_DB_PATH = BASE_DIR / "data" / "safe_routes.db"

router = APIRouter(prefix="/crime", tags=["Crime Reporting"])


def _safe_add_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except sqlite3.OperationalError:
        pass


def _create_index(conn: sqlite3.Connection, name: str, ddl: str) -> None:
    conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {ddl}")

# ---------------------------------------------------------------------------
# 1. Pydantic Schema
# ---------------------------------------------------------------------------
class CrimeReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_id: str = Field(min_length=1, max_length=128)
    incident_type: str = Field(min_length=1, max_length=64)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    timestamp: str = Field(min_length=4, max_length=64)


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------
def init_crime_db():
    """Ensure the crime_reports table exists."""
    with sqlite3.connect(CRIME_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crime_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                incident_type TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        _safe_add_column(conn, "crime_reports", "severity", "REAL DEFAULT 5.0")
        _safe_add_column(conn, "crime_reports", "crime_type", "TEXT DEFAULT 'unknown'")
        _safe_add_column(conn, "crime_reports", "confidence_score", "REAL DEFAULT 1.0")
        _safe_add_column(conn, "crime_reports", "reported_by", "TEXT DEFAULT 'anonymous'")
        _safe_add_column(conn, "crime_reports", "time_of_day", "TEXT")
        _safe_add_column(conn, "crime_reports", "area_type", "TEXT")

        _create_index(conn, "idx_crime_reports_user_id", "crime_reports (user_id)")
        _create_index(conn, "idx_crime_reports_timestamp", "crime_reports (timestamp)")
        _create_index(conn, "idx_crime_reports_incident_type", "crime_reports (incident_type)")
        _create_index(conn, "idx_crime_reports_lat_lng", "crime_reports (lat, lng)")
        _create_index(conn, "idx_crime_reports_date", "crime_reports (date(timestamp))")
        conn.commit()


def init_safe_routes_db():
    """Ensure the safe_routes helper table exists with useful indexes."""
    with sqlite3.connect(SAFE_ROUTES_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS road_segments (
                edge_id TEXT PRIMARY KEY,
                safety_score REAL DEFAULT 100.0
            )
            """
        )
        _create_index(conn, "idx_road_segments_safety_score", "road_segments (safety_score)")
        conn.commit()

# Call initialization on module load
init_crime_db()
init_safe_routes_db()


# ---------------------------------------------------------------------------
# Mock Function: Nearest Road Segment
# ---------------------------------------------------------------------------
def find_nearest_road_segment_mock(lat: float, lng: float) -> str:
    """
    Mock logic to find the nearest road segment.
    In a real scenario, this would use an R-tree or spatial query (PostGIS/SpatiaLite)
    against the road graph to find the closest edge.
    
    Here, we deterministically mock an edge_id based on the coordinates 
    so it resolves to something we can 'update' in safe_routes.db.
    """
    # Deterministic mock segment ID generation
    mock_id = int((abs(lat) + abs(lng)) * 1000) % 10000 
    return f"edge_{mock_id}"


# ---------------------------------------------------------------------------
# Database Function: Update Safety Score
# ---------------------------------------------------------------------------
def update_segment_safety_score(segment_id: str, incident_type: str) -> float:
    """
    Dynamically updates the safety score for a given segment in safe_routes.db
    using the Incident Severity Classification module.
    """
    with sqlite3.connect(SAFE_ROUTES_DB_PATH) as conn:
        # 1. Ensure a table exists (in case safe_routes.db is empty for this test)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS road_segments (
                edge_id TEXT PRIMARY KEY,
                safety_score REAL DEFAULT 100.0
            )
            """
        )
        
        # 2. Try to fetch existing score
        cursor = conn.execute(
            "SELECT safety_score FROM road_segments WHERE edge_id = ?", 
            (segment_id,)
        )
        row = cursor.fetchone()
        
        if row:
            current_score = row[0]
            new_score = calculate_new_safety_score(current_score, incident_type)
            conn.execute(
                "UPDATE road_segments SET safety_score = ? WHERE edge_id = ?",
                (new_score, segment_id)
            )
        else:
            # Insert new mock segment if it didn't exist (assuming default 100 base)
            new_score = calculate_new_safety_score(100.0, incident_type)
            conn.execute(
                "INSERT INTO road_segments (edge_id, safety_score) VALUES (?, ?)",
                (segment_id, new_score)
            )
            
        conn.commit()
        return new_score


# ---------------------------------------------------------------------------
# API Route
# ---------------------------------------------------------------------------
@router.post("/report")
async def handle_crime_report(report: CrimeReportInput, request: Request):
    """
    Receives a crime report, logs it to crime_reports.db,
    finds the nearest road segment, and updates its safety score in safe_routes.db.
    """
    try:
        enforce_rate_limit(
            request,
            scope="crime.report",
            limit=CRIME_RATE_LIMIT_REQUESTS,
            window_seconds=CRIME_RATE_LIMIT_WINDOW_SECONDS,
            subject=report.user_id,
        )

        if not coords_in_bounds(report.lat, report.lng):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Crime report coordinates are outside the supported area. "
                    f"Bounds: lat [{BOUNDS['min_lat']}, {BOUNDS['max_lat']}], "
                    f"lng [{BOUNDS['min_lng']}, {BOUNDS['max_lng']}]"
                ),
            )

        # STEP 1: Log the report into crime_reports.db
        with sqlite3.connect(CRIME_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO crime_reports (user_id, incident_type, lat, lng, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (report.user_id, report.incident_type, report.lat, report.lng, report.timestamp)
            )
            conn.commit()

        # STEP 2: Find the nearest road segment (Mock logic)
        nearest_segment_id = find_nearest_road_segment_mock(report.lat, report.lng)

        # STEP 3: Dynamically update the safety score in safe_routes.db
        new_score = update_segment_safety_score(
            segment_id=nearest_segment_id, 
            incident_type=report.incident_type
        )

        # STEP 4: Invalidate Dijkstra NetworkX Cached Routes
        # We import here to avoid circular dependencies with ai/main.py
        from main import route_cache
        from services.crime_heatmap_service import get_heatmap_service
        from services.danger_zone_detector import get_danger_zone_detector
        from services.route_service import invalidate_graph_cache
        route_cache.clear()
        invalidate_graph_cache()
        get_heatmap_service().invalidate_cache()
        get_danger_zone_detector().invalidate_cache()

        return {
            "status": "success",
            "message": "Crime report logged and safety score updated.",
            "data": {
                "user_id": report.user_id,
                "incident_type": report.incident_type,
                "nearest_segment_id": nearest_segment_id,
                "new_safety_score": new_score
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
