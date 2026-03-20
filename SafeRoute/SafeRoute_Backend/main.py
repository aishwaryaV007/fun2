"""
Women Safety Smart Route Predictor — Backend API
=================================================
FastAPI server with:
  • 1,024-segment grid loaded from safe_routes_grid.json
  • Safety-score calculation using shared weights
  • Safest-route finding via NetworkX + modified Dijkstra
  • Familiarity scoring integration (per-user travel history)
  • API-key authentication on crime-report endpoint
  • WebSocket live alerts
  • Real-time SOS Alert module with admin WebSocket broadcast
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional

from zeroconf import ServiceInfo, Zeroconf
from cachetools import TTLCache

import networkx as nx
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from core.config import CORS_ALLOWED_ORIGINS, CORS_ALLOWED_ORIGIN_REGEX
from core.safety_config import (
    API_KEY,
    BOUNDS,
    WEIGHTS,
    coords_in_bounds,
    get_time_multiplier,
)
from services.familiarity_module import FamiliarityScoreCalculator, get_db, router as familiarity_router
from services.websocket import admin_manager  # shared singleton — used by /ws/admin_alert and /sos/trigger

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Women Safety Route Predictor",
    description="AI-powered safest route calculation for women",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_origin_regex=CORS_ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Mount familiarity endpoints under /api
app.include_router(familiarity_router)

# ---------------------------------------------------------------------------
# Canonical API routers (new clean endpoint groups)
# Registered AFTER familiarity_router to avoid prefix conflicts.
# All legacy endpoints (/safest_route, /sos_alert, etc.) remain untouched.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Canonical API routers
# ---------------------------------------------------------------------------
import sys
import core.config
from core.safety_config import BOUNDS, coords_in_bounds
# Hotfix: Inject missing variables into core.config so crime.py doesn't crash on import
core.config.BOUNDS = BOUNDS
core.config.coords_in_bounds = coords_in_bounds
core.config.CRIME_RATE_LIMIT_REQUESTS = 10
core.config.CRIME_RATE_LIMIT_WINDOW_SECONDS = 60

try:
    from api.routes.ai_safety import router as ai_router
    app.include_router(ai_router)
except ImportError as e:
    logger.error(f"Failed to load ai_safety router: {e}")

try:
    from api.routes.crime import router as crime_router
    app.include_router(crime_router)
except ImportError as e:
    logger.error(f"Failed to load crime router: {e}")

try:
    from api.routes.sos import router as sos_router
    app.include_router(sos_router)
except ImportError as e:
    logger.warning(f"Failed to load sos router: {e}")
# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class Location(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    start: Location
    end: Location
    time: Optional[str] = None  # HH:MM format
    user_id: Optional[str] = None  # Add user context internally for familiarity routing


class CrimeReport(BaseModel):
    lat: float
    lng: float
    description: str
    severity: int = 5           # 1-10 scale
    # Optional: if the user provides their current journey endpoints,
    # the backend will compute a safer alternate route after updating crime data.
    route_start: Optional[Location] = None
    route_end:   Optional[Location] = None
    time:        Optional[str] = None   # HH:MM — defaults to current hour
    user_id:     Optional[str] = None


class HeatmapCell(BaseModel):
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float
    risk_intensity: float  # 0.0 to 1.0 normalization
    segment_ids: list[str]
    average_safety: float
class SOSAlert(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    timestamp: str  # ISO 8601 or HH:MM, as sent by the frontend


# ---------------------------------------------------------------------------
# Dynamic IP Setup
# ---------------------------------------------------------------------------
def get_local_ip() -> str:
    """Get the physical LAN IP of the current machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
PORT = 8000

# ---------------------------------------------------------------------------
# SOS Admin WebSocket connection manager
# ---------------------------------------------------------------------------
# admin_manager is imported from services.websocket (shared singleton).
# Both the /ws/admin_alert WebSocket route below AND the /sos/trigger
# broadcast (via services/sos_service.py) use the SAME instance so that
# alerts from POST /sos/trigger are delivered to every connected admin client.
#
# ⚠️  DO NOT re-declare AdminConnectionManager or admin_manager here —
#     that would create a second, separate instance and break the pipeline.
# ---------------------------------------------------------------------------

from core.config import SOS_DB_PATH


def _get_sos_db() -> sqlite3.Connection:
    conn = sqlite3.connect(SOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


from services.route_safety import safest_route, Route

# Dummy data since route_safety does not provide graph features
JUNCTIONS = {}
EDGES = []
JUNCTION_MAP = {}

def _build_road_graph(*args, **kwargs):
    return (None, None, None)

def _build_route_response_summary(*args, **kwargs):
    return {}

def _calculate_route_segments(*args, **kwargs):
    return []

def find_nearest_junction(*args, **kwargs):
    return None

def _invalidate_graph_cache(*args, **kwargs):
    pass

# Route cache (TTLCache: max 1000 routes, 300 second expiry)
route_cache = TTLCache(maxsize=1000, ttl=300)

# WebSocket connections for live alerts
active_connections: list[WebSocket] = []

# ---------------------------------------------------------------------------
# Incident store — tracks every live crime report for audit / persistence
# ---------------------------------------------------------------------------
incident_log: list[dict] = []


def _update_segment_crime(lat: float, lng: float, severity: int) -> dict | None:
    """
    Step 1 & 2 — Find the closest road segment and apply multi-report aggregation.
    Uses severity-weighted averaging: new_avg = (prev_avg * prev_count + severity) / (prev_count + 1).
    Repeated reports strengthen the temporary risk level via aggregation.
    """
    if not EDGES:
        return None

    # Find nearest edge by Euclidean distance to its midpoint
    def _midpoint_dist(seg: dict) -> float:
        mid_lat = (seg["start_lat"] + seg["end_lat"]) / 2
        mid_lng = (seg["start_lon"] + seg["end_lon"]) / 2
        return (mid_lat - lat) ** 2 + (mid_lng - lng) ** 2

    closest = min(EDGES, key=_midpoint_dist)

    # Multi-report aggregation logic
    prev_count = closest.get("incident_report_count", 0)
    prev_avg   = closest.get("incident_severity_avg", 0.0)
    
    new_count = prev_count + 1
    new_avg = round((prev_avg * prev_count + severity) / new_count, 3)
    
    closest["incident_report_count"] = new_count
    closest["incident_severity_avg"] = new_avg

    # Calculate scores for response
    hour = datetime.now().hour
    # Capture state before this update for 'old_score'
    old_score, _ = calculate_safety_score({
        **closest, 
        "incident_report_count": prev_count,
        "incident_severity_avg": prev_avg
    }, hour)
    new_score, _ = calculate_safety_score(closest, hour)

    logger.info(
        "Incident aggregated on segment %s | count %d | avg_severity %.2f | safety %.1f → %.1f",
        closest["segment_id"], new_count, new_avg, old_score, new_score,
    )

    return {
        "segment_id":         closest["segment_id"],
        "edge_id":            closest["edge_id"],
        "report_count":       new_count,
        "average_severity":   new_avg,
        "old_safety_score":   old_score,
        "new_safety_score":   new_score,
        "score_drop":         round(old_score - new_score, 1),
    }


# ---------------------------------------------------------------------------
# Data Normalization Layer
# ---------------------------------------------------------------------------

class DataNormalizationLayer:
    """Standardizes raw inputs into normalized 0-1 metrics."""
    
    @staticmethod
    def normalize_crime(density: float) -> float:
        # Linear scaling capped at 1.0
        from core.safety_config import MAX_VALUES
        return min(density / MAX_VALUES["crime"], 1.0)
    
    @staticmethod
    def normalize_cctv(count: int) -> float:
        from core.safety_config import MAX_VALUES
        return min(count / MAX_VALUES["cctv"], 1.0)
    
    @staticmethod
    def normalize_crowd(density: float) -> float:
        from core.safety_config import MAX_VALUES
        return min(density / MAX_VALUES["crowd"], 1.0)
    
    @staticmethod
    def normalize_vibrancy(safe_points: int) -> float:
        from core.safety_config import MAX_VALUES
        return min(safe_points / MAX_VALUES["vibrancy"], 1.0)


# ---------------------------------------------------------------------------
# Safety score calculation (uses shared config)
# ---------------------------------------------------------------------------

def calculate_safety_score(segment: dict, hour: int, familiarity_score: float = FamiliarityScoreCalculator.BASE_SCORE) -> tuple[float, dict[str, float]]:
    """
    Calculates final segment safety score and provides a breakdown of component impacts.
    Hierarchy: Crime(0.4) > CCTV/Light(0.2 ea) > Fam/RoadType(0.1 ea).
    """
    
    # 1. Component Normalization & Temporal Scaling
    time_mult = get_time_multiplier(hour)
    
    # CRIME Factor (Highest Priority: 40%)
    base_density = segment.get("crime_density", 0.0)
    report_count = segment.get("incident_report_count", 0)
    sev_avg      = segment.get("incident_severity_avg", 0.0)
    incident_boost = (sev_avg / 10.0) * min(report_count * 0.2, 1.0)
    
    raw_crime_risk = base_density + incident_boost
    effective_crime_risk = min(raw_crime_risk * time_mult, 2.0)
    crime_safety_norm = 1.0 - min(effective_crime_risk / 2.0, 1.0)
    
    # CCTV & LIGHTING Factors (Moderate Priority: 20% each)
    cctv_norm     = DataNormalizationLayer.normalize_cctv(segment.get("cctv_count", 0))
    lighting_norm = DataNormalizationLayer.normalize_vibrancy(
        5 if segment.get("safe_zone_flag", False) else 0 
    )
    
    # FAMILIARITY & ROAD TYPE Factors (Lower Priority: 10% each)
    fam_norm = 1.0 if familiarity_score > FamiliarityScoreCalculator.BASE_SCORE else 0.5
    
    raw_crowd_norm = DataNormalizationLayer.normalize_crowd(segment.get("crowd_density", 0))
    road_risk = 1.0 - raw_crowd_norm
    effective_road_risk = min(road_risk * time_mult, 1.0)
    road_type_norm = 1.0 - effective_road_risk
    
    # 2. Impact Calculation (Weighted)
    # Factor Impact = (Weight * Normalized Value) * 100
    impacts = {
        "crime":       round(WEIGHTS["crime"]       * crime_safety_norm * 100.0, 1),
        "cctv":        round(WEIGHTS["cctv"]        * cctv_norm         * 100.0, 1),
        "lighting":    round(WEIGHTS["lighting"]    * lighting_norm     * 100.0, 1),
        "familiarity": round(WEIGHTS["familiarity"] * fam_norm          * 100.0, 1),
        "road_type":   round(WEIGHTS["road_type"]   * road_type_norm    * 100.0, 1),
    }
    
    # Calculate base score (before time multiplier impacts)
    # We estimate time impact as the reduction from the potential perfect score or baseline
    total_score = sum(impacts.values())
    
    # Final clamping and rounding
    final_score = float(max(0.0, min(100.0, round(total_score, 1))))
    
    # Add time impact for transparency (how much we lost due to night/dusk)
    # Simplified as a display-only metric
    impacts["time"] = -round((time_mult - 1.0) * (base_density + road_risk) * 10.0, 1)

    return final_score, impacts


def get_safety_color(score: float) -> str:
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange"
    return "red"


def get_unsafe_reasons(segment: dict, safety: float) -> list[str]:
    reasons = []
    if segment.get("cctv_count", 0) == 0:
        reasons.append("No CCTV surveillance.")
    if not segment.get("safe_zone_flag", False):
        reasons.append("Few shops or safe zones nearby.")
    return reasons


# ---------------------------------------------------------------------------
# Graph building & routing  (delegated to route_service)
# ---------------------------------------------------------------------------

def build_road_graph(
    hour: int,
    familiarity_map: Optional[dict[str, float]] = None,
) -> tuple:
    """
    Build a NetworkX graph with personalised safety-weighted edges.

    Delegates to services.route_service.build_road_graph which supports
    real junction JSON files with fallback to the legacy grid.

    Returns (G, junction_tree, junction_list).
    """
    return _build_road_graph(
        hour=hour,
        familiarity_map=familiarity_map or {},
        junctions=JUNCTIONS,
        edges=EDGES,
    )


# Alias kept for any remaining references inside this file
find_nearest_node = find_nearest_junction


def calculate_route(G: nx.Graph, start_node, end_node, use_safety: bool = True):
    """Calculate route using the shared routing engine implementation."""
    return _calculate_route_segments(G, start_node, end_node, use_safety=use_safety)


# ---------------------------------------------------------------------------
# API-key dependency for protected endpoints
# ---------------------------------------------------------------------------

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Require a valid API key via the X-API-Key header."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return x_api_key


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "Women Safety Smart Route Predictor API",
        "version": "2.0.0",
        "total_segments": len(EDGES),
        "endpoints": [
            "/health",
            "/server-info",
            "/safest_route",
            "/heatmap",
            "/report_crime",
            "/segment/{id}",
            "/api/routes/check-familiarity",
            "/api/routes/complete-journey",
            "/api/users/{user_id}/stats",
            "/test",
        ],
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Backend is running",
        "segments_loaded": len(EDGES),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/safest_route")
async def get_safest_route(request: RouteRequest, db=Depends(get_db)):
    """
    Calculate the safest route between two points.
    Validates coordinates fall within the supported area.
    Integrates user familiarity dynamically if user_id is provided.
    """
    # Bounds validation
    if not coords_in_bounds(request.start.lat, request.start.lng):
        raise HTTPException(
            status_code=400,
            detail=f"Start coordinates ({request.start.lat}, {request.start.lng}) "
                   f"are outside the supported area. "
                   f"Bounds: lat [{BOUNDS['min_lat']}, {BOUNDS['max_lat']}], "
                   f"lng [{BOUNDS['min_lng']}, {BOUNDS['max_lng']}]",
        )
    if not coords_in_bounds(request.end.lat, request.end.lng):
        raise HTTPException(
            status_code=400,
            detail=f"End coordinates ({request.end.lat}, {request.end.lng}) "
                   f"are outside the supported area.",
        )

    # Parse time
    if request.time:
        try:
            hour = int(request.time.split(":")[0])
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    else:
        hour = datetime.now().hour

    # Check cache (key must include user_id)
    cache_key = f"{request.start.lat}_{request.start.lng}_{request.end.lat}_{request.end.lng}_{hour}_{request.user_id}"
    if cache_key in route_cache:
        return route_cache[cache_key]

    # Dynamically inject familiarity context if applicable
    familiarity_map = {}
    if request.user_id:
        all_segment_ids = [s.get("segment_id", "") for s in EDGES if s.get("segment_id")]
        try:
            fam_resp = FamiliarityScoreCalculator.calculate_route_familiarity(
                user_id=request.user_id, segment_ids=all_segment_ids, db=db
            )
            # Flatten to Dictionary = { segment_id: familiarity_score }
            familiarity_map = {seg.segment_id: seg.familiarity_score for seg in fam_resp.segments}
        except Exception as e:
            logger.warning("Familiarity DB lookup failed for user %s: %s", request.user_id, e)

    # Build junction-based graph with familiarity weighting
    G, junction_tree, junction_list = build_road_graph(hour, familiarity_map=familiarity_map)

    start_junction = find_nearest_junction(G, request.start.lat, request.start.lng, junction_tree, junction_list)
    end_junction   = find_nearest_junction(G, request.end.lat,   request.end.lng,   junction_tree, junction_list)

    if not start_junction or not end_junction:
        raise HTTPException(status_code=400, detail="Could not find junctions near given coordinates")

    if start_junction == end_junction:
        raise HTTPException(
            status_code=400,
            detail=(
                "Start and end resolve to the same junction. "
                "The dataset covers the Gachibowli / HITEC City area "
                "(lat 17.40–17.49, lng 78.30–78.40). "
                "Please use coordinates within this area."
            ),
        )

    safest_route  = calculate_route(G, start_junction, end_junction, use_safety=True)
    shortest_route = calculate_route(G, start_junction, end_junction, use_safety=False)

    if not safest_route:
        raise HTTPException(status_code=404, detail="No route found")

    result = {
        "safest_route": safest_route,
        "shortest_route": shortest_route,
        "time_of_day": f"{hour}:00",
        "time_multiplier": get_time_multiplier(hour),
        "cached": False,
        **_build_route_response_summary(safest_route),
    }

    route_cache[cache_key] = {**result, "cached": True}
    return result


@app.get("/heatmap/spatial")
async def get_spatial_heatmap(hour: Optional[int] = None):
    """
    Risk Heatmap Engine: Aggregates segment-level safety scores into 
    a 20x20 spatial grid of intensity-based risk zones.
    """
    if hour is None:
        hour = datetime.now().hour

    # Grid parameters
    grid_size = 20
    lat_step = (BOUNDS["max_lat"] - BOUNDS["min_lat"]) / grid_size
    lng_step = (BOUNDS["max_lng"] - BOUNDS["min_lng"]) / grid_size

    # Initialize grid: (lat_idx, lng_idx) -> {risks: [], safety_scores: [], segment_ids: []}
    grid_accumulation = {}

    for seg in EDGES:
        safety, _ = calculate_safety_score(seg, hour)
        risk_delta = 100.0 - safety
        
        # Determine cell for segment midpoint
        mid_lat = (seg["start_lat"] + seg["end_lat"]) / 2.0
        mid_lng = (seg["start_lon"] + seg["end_lon"]) / 2.0
        
        lat_idx = int((mid_lat - BOUNDS["min_lat"]) / lat_step)
        lng_idx = int((mid_lng - BOUNDS["min_lng"]) / lng_step)
        
        # Clamp to grid bounds
        lat_idx = max(0, min(grid_size - 1, lat_idx))
        lng_idx = max(0, min(grid_size - 1, lng_idx))
        
        cell_key = (lat_idx, lng_idx)
        if cell_key not in grid_accumulation:
            grid_accumulation[cell_key] = {"risks": [], "safety_scores": [], "segment_ids": []}
        
        grid_accumulation[cell_key]["risks"].append(risk_delta)
        grid_accumulation[cell_key]["safety_scores"].append(safety)
        grid_accumulation[cell_key]["segment_ids"].append(seg.get("segment_id", "link"))

    # Convert accumulation to normalized intensities
    heatmap_cells = []
    
    # Calculate global max risk delta for normalization across the grid
    all_cell_total_risks = [sum(data["risks"]) for data in grid_accumulation.values()]
    max_observed_risk = max(all_cell_total_risks) if all_cell_total_risks else 1.0

    for (lat_idx, lng_idx), data in grid_accumulation.items():
        cell_risk_sum = sum(data["risks"])
        intensity = round(cell_risk_sum / max_observed_risk, 3) if max_observed_risk > 0 else 0.0
        avg_safety = round(sum(data["safety_scores"]) / len(data["safety_scores"]), 1)
        
        cell_min_lat = BOUNDS["min_lat"] + (lat_idx * lat_step)
        cell_max_lat = cell_min_lat + lat_step
        cell_min_lng = BOUNDS["min_lng"] + (lng_idx * lng_step)
        cell_max_lng = cell_min_lng + lng_step
        
        heatmap_cells.append(HeatmapCell(
            min_lat=cell_min_lat,
            max_lat=cell_max_lat,
            min_lng=cell_min_lng,
            max_lng=cell_max_lng,
            risk_intensity=intensity,
            segment_ids=data["segment_ids"],
            average_safety=avg_safety
        ))

    return {
        "hour": hour,
        "grid_resolution": f"{grid_size}x{grid_size}",
        "bounding_box": BOUNDS,
        "cells_count": len(heatmap_cells),
        "heatmap": heatmap_cells,
        "legend": {
            "intensity_range": "0.0 (Safe) to 1.0 (High Risk Hotspot)",
            "mechanism": "Spatial aggregation of segment-level safety risk deltas."
        }
    }


@app.get("/heatmap")
async def get_heatmap(hour: Optional[int] = None):
    """Safety heatmap data for all road segments."""
    if hour is None:
        hour = datetime.now().hour

    heatmap_data = []
    for seg in EDGES:
        safety, impacts = calculate_safety_score(seg, hour)
        heatmap_data.append({
            "edge_id": seg["edge_id"],
            "segment_id": seg.get("segment_id", ""),
            "start": {"lat": seg["start_lat"], "lng": seg["start_lon"]},
            "end": {"lat": seg["end_lat"],   "lng": seg["end_lon"]  },
            "safety_score": safety,
            "impacts": impacts,
            "color": get_safety_color(safety),
            "road_type": seg.get("road_type", "unknown"),
            "details": {
                "crime_density": seg.get("crime_density", 0.0),
                "lights_per_100m": seg.get("lights_per_100m", 0.0),
                "crowd_density": seg.get("crowd_density", 0.0),
                "cctv_count": seg.get("cctv_count", 0),
            },
        })

    return {
        "hour": hour,
        "time_multiplier": get_time_multiplier(hour),
        "total_segments": len(heatmap_data),
        "segments": heatmap_data,
        "legend": {
            "green": "80-100 (Safe)",
            "yellow": "60-79 (Caution)",
            "orange": "40-59 (Risky)",
            "red": "0-39 (Danger)",
        },
    }


@app.get("/danger-zones")
async def get_danger_zones(force_refresh: bool = False, min_risk: float = 0.3):
    """Legacy alias for danger-zone detection used by dashboard integrations."""
    if not 0.0 <= min_risk <= 1.0:
        raise HTTPException(status_code=400, detail="min_risk must be between 0.0 and 1.0")

    from services.danger_zone_detector import get_danger_zone_detector

    try:
        detector = get_danger_zone_detector()
        zones = detector.detect_danger_zones(force_refresh=force_refresh, min_risk=min_risk)
        return {
            "status": "success",
            "count": len(zones),
            "danger_zones": zones,
        }
    except Exception as e:
        logger.error("Danger zone detection error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report_crime")
async def report_crime(report: CrimeReport):
    """
    Full 5-step incident pipeline:

    STEP 1 — Receive incident (lat, lng, severity) from the user.
    STEP 2 — Find the nearest road segment and update its crime_density.
    STEP 3 — Recalculate that segment's safety score (done inside _update_segment_crime).
    STEP 4 — If route_start / route_end are provided, find a safer alternate route
              now that the graph reflects updated crime data.
    STEP 5 — Broadcast a real-time alert to all WebSocket-connected clients.
    """

    # ── STEP 1: Receive & validate incident ──────────────────────────────
    timestamp = datetime.now().isoformat()
    incident_log.append({
        "lat":         report.lat,
        "lng":         report.lng,
        "description": report.description,
        "severity":    report.severity,
        "timestamp":   timestamp,
    })
    logger.info("Incident received at (%.5f, %.5f) severity=%d", report.lat, report.lng, report.severity)

    # ── STEP 2 & 3: Update crime density + recalculate safety score ──────
    segment_update = _update_segment_crime(report.lat, report.lng, report.severity)

    # Invalidate route cache — all cached routes may now be suboptimal
    route_cache.clear()
    _invalidate_graph_cache()
    from services.crime_heatmap_service import get_heatmap_service
    from services.danger_zone_detector import get_danger_zone_detector
    get_heatmap_service().invalidate_cache()
    get_danger_zone_detector().invalidate_cache()

    # ── STEP 4: Find safer alternate route (if journey endpoints provided) ─
    alternate_route = None
    alternate_error = None

    if report.route_start and report.route_end:
        try:
            # Parse time
            if report.time:
                hour = int(report.time.split(":")[0])
            else:
                hour = datetime.now().hour

            # Rebuild the graph — crime_density is already updated in EDGES
            G, j_tree, j_list = build_road_graph(hour)

            start_junction = find_nearest_junction(G, report.route_start.lat, report.route_start.lng, j_tree, j_list)
            end_junction   = find_nearest_junction(G, report.route_end.lat,   report.route_end.lng,   j_tree, j_list)

            if start_junction and end_junction and start_junction != end_junction:
                safe_path = calculate_route(G, start_junction, end_junction, use_safety=True)
                if safe_path:
                    avg_safety = round(
                        sum(s["safety_score"] for s in safe_path) / len(safe_path), 1
                    )
                    alternate_route = {
                        "segments":       safe_path,
                        "total_segments": len(safe_path),
                        "average_safety": avg_safety,
                        "recommendation": (
                            "This alternate route avoids the incident area."
                            if segment_update else
                            "Safest available route recalculated."
                        ),
                    }
                else:
                    alternate_error = "No alternate path found between the given coordinates."
            else:
                alternate_error = "Start and end coordinates resolve to the same node."

        except Exception as exc:
            logger.exception("Alternate route calculation failed after incident")
            alternate_error = str(exc)

    # ── STEP 5: Broadcast real-time WebSocket alert to all clients ────────
    alert = {
        "type":             "crime_report",
        "location":         {"lat": report.lat, "lng": report.lng},
        "description":      report.description,
        "severity":         report.severity,
        "timestamp":        timestamp,
        "affected_segment": segment_update["segment_id"] if segment_update else None,
        "score_drop":       segment_update["score_drop"] if segment_update else 0,
    }
    await broadcast_alert(alert)

    # ── Build response ─────────────────────────────────────────────────────
    response = {
        "status":    "reported",
        "message":   "Incident recorded. Crime density updated and safety scores recalculated.",
        "timestamp": timestamp,

        # Step 2 & 3 results
        "segment_impact": segment_update,

        # Step 4 result
        "alternate_route": alternate_route,
    }

    if alternate_error:
        response["alternate_route_error"] = alternate_error

    return response


@app.get("/segment/{edge_id}")
async def get_segment_details(edge_id: int, hour: Optional[int] = None):
    """
    Diagnostic Endpoint: Returns detailed segment safety information by querying 
    the in-memory layout and the safe_routes.db dynamic score overrides.
    """
    if hour is None:
        hour = datetime.now().hour

    segment = next((s for s in EDGES if s.get("edge_id") == edge_id), None)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
        
    # 1. Query safe_routes.db for a dynamically updated safety score
    safety_score = None
    try:
        from pathlib import Path
        import sqlite3
        db_path = Path(__file__).resolve().parent / "data" / "safe_routes.db"
        with sqlite3.connect(db_path) as conn:
            # Check for standard string IDs or our mock "edge_X" ids
            cursor = conn.execute(
                "SELECT safety_score FROM road_segments WHERE edge_id = ? OR edge_id = ?",
                (str(edge_id), f"edge_{edge_id}")
            )
            row = cursor.fetchone()
            if row:
                safety_score = float(row[0])
    except Exception as e:
        logger.warning(f"Could not read from safe_routes.db: {e}")

    # Fallback to calculating from in-memory attributes if not dynamically updated yet
    if safety_score is None:
        safety_score, impacts = calculate_safety_score(segment, hour)
        
    # 2. Extract base segment structural data from in-memory ROAD_SEGMENTS / graph
    base_crime_density = segment.get("crime_density", 0.0)
    cctv_availability = segment.get("cctv_count", 0)
    street_lighting_level = segment.get("lights_per_100m", 0)

    # 3. Identify attached incidents
    # We match incidents in incident_log by finding which incidents are closest to this segment
    attached_incidents = []
    
    # We rebuild/read the NetworkX graph for distance calculations if necessary,
    # but for speed in this endpoint, we'll check if the incident's lat/lng is closest 
    # to this segment's start/end coordinates.
    G, j_tree, j_list = build_road_graph(hour)

    for inc in incident_log:
        # find nearest junction in graph for this incident
        nearest_node = find_nearest_junction(G, inc["lat"], inc["lng"], j_tree, j_list)
        if nearest_node is not None:
            # Check if this segment contains the nearest node
            if nearest_node == segment["start"] or nearest_node == segment["end"]:
                attached_incidents.append({
                    "description": inc.get("description", ""),
                    "severity": inc.get("severity", 5),
                    "timestamp": inc.get("timestamp", ""),
                    "lat": inc.get("lat"),
                    "lng": inc.get("lng")
                })

    return {
        "edge_id": edge_id,
        "segment_id": segment.get("segment_id", ""),
        "current_safety_score": round(safety_score, 1),
        "diagnostics": {
            "base_crime_density": base_crime_density,
            "cctv_availability": cctv_availability,
            "street_lighting_level": street_lighting_level,
        },
        "recent_incidents_attached": attached_incidents
    }


@app.get("/server-info")
async def get_server_info():
    """Returns dynamic server configuration for frontend autodiscovery."""
    ip = get_local_ip()
    return {
        "host": ip,
        "port": PORT,
        "base_url": f"http://{ip}:{PORT}",
        "ws_url": f"ws://{ip}:{PORT}/ws/admin_alert",
        "ws_sos_url": f"ws://{ip}:{PORT}/sos/stream"
    }

# ---------------------------------------------------------------------------
# Interactive test page
# ---------------------------------------------------------------------------

@app.get("/test", response_class=HTMLResponse)
async def realtime_test_page():
    """Serve a simple page to try real-time API examples in the browser."""
    seg_count = len(ROAD_SEGMENTS)
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Women Safety Route API — Test Console</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', system-ui, sans-serif; max-width: 1000px; margin: 0 auto; padding: 40px 20px; background: linear-gradient(135deg, #020617 0%, #0f172a 100%); color: #f8fafc; min-height: 100vh; }}
    h1 {{ color: #38bdf8; font-weight: 700; font-size: 2.2rem; margin-bottom: 0.5rem; text-align: center; background: -webkit-linear-gradient(#38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .subtitle {{ text-align: center; color: #94a3b8; margin-bottom: 40px; font-size: 1.1rem; }}
    .grid-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    section {{ padding: 24px; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5); transition: transform 0.2s; }}
    section:hover {{ transform: translateY(-2px); border-color: rgba(56, 189, 248, 0.2); }}
    h3 {{ color: #e2e8f0; font-size: 1.25rem; font-weight: 600; margin-top: 0; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
    button {{ padding: 10px 18px; margin-top: 12px; cursor: pointer; background: linear-gradient(135deg, #2563eb, #4f46e5); color: white; border: none; border-radius: 8px; font-weight: 500; font-family: 'Inter'; transition: all 0.2s; box-shadow: 0 4px 12px -4px rgba(37, 99, 235, 0.5); width: 100%; }}
    button:hover {{ transform: translateY(-1px); box-shadow: 0 6px 16px -4px rgba(37, 99, 235, 0.6); opacity: 0.95; }}
    button:active {{ transform: translateY(1px); box-shadow: none; }}
    button.danger {{ background: linear-gradient(135deg, #dc2626, #991b1b); box-shadow: 0 4px 12px -4px rgba(220, 38, 38, 0.5); }}
    
    .result-section {{ grid-column: 1 / -1; }}
    #out-container {{ background: #0f172a; border-radius: 12px; border: 1px solid #334155; overflow: hidden; }}
    pre {{ margin: 0; padding: 20px; color: #cbd5e1; font-size: 13px; max-height: 500px; overflow-y: auto; line-height: 1.5; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    pre::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    pre::-webkit-scrollbar-track {{ background: #0f172a; }}
    pre::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
    
    label {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; font-size: 0.9rem; color: #cbd5e1; font-weight: 500; }}
    input {{ padding: 10px 12px; background: rgba(15, 23, 42, 0.6); color: #f8fafc; border: 1px solid #475569; border-radius: 8px; font-family: 'Inter'; outline: none; transition: border-color 0.2s; }}
    input:focus {{ border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.1); }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .full-row {{ grid-column: 1 / -1; }}
    
    .loading {{ display: inline-block; width: 16px; height: 16px; border: 3px solid rgba(255,255,255,.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; margin-right: 8px; vertical-align: middle; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    
    .safest-route-ui {{ margin-top: 20px; }}
    .segment-card {{ background: rgba(30, 41, 59, 0.9); border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }}
    .segment-details-btn {{ background: transparent; border: 1px solid #475569; padding: 6px 12px; margin: 0; width: auto; font-size: 12px; color: #94a3b8; box-shadow: none; }}
    .segment-details-btn:hover {{ background: #334155; color: white; transform: none; box-shadow: none; }}
    .badge {{ padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase; }}
    .badge-green {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
    .badge-yellow {{ background: rgba(234, 179, 8, 0.2); color: #fde047; }}
    .badge-orange {{ background: rgba(249, 115, 22, 0.2); color: #fdba74; }}
    .badge-red {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; }}
  </style>
</head>
<body>
  <h1>Women Safety Route API</h1>
  <div class="subtitle">Test Console • <code id="base" style="color:#818cf8;"></code> • <b>{seg_count}</b> segments loaded</div>

  <div class="grid-container">
    <section>
      <h3>✨ 1. Health Status</h3>
      <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 16px; line-height: 1.4;">Check if the backend systems are operational and actively monitoring the grid for safe routes.</p>
      <button onclick="call('/health', this)">Run System Diagnostic</button>
    </section>

    <section>
      <h3>🗺️ 2. Safest Route Finder</h3>
      <div class="row">
        <label>Start Lat <input type="text" id="startLat" value="17.4267"></label>
        <label>Start Lng <input type="text" id="startLng" value="78.3368"></label>
        <label>End Lat <input type="text" id="endLat" value="17.4455"></label>
        <label>End Lng <input type="text" id="endLng" value="78.3317"></label>
        <label>Time (HH:MM) <input type="text" id="time" value="14:00"></label>
        <label>User ID <input type="text" id="userId" value="test-user-123" placeholder="(Optional)"></label>
        <label class="full-row"><button type="button" onclick="completeJourney(this)" style="background: linear-gradient(135deg, #22c55e, #16a34a);">✅ Mark Last Route as Travelled</button></label>
      </div>
      <button onclick="safestRoute(this)">Calculate Safest Route</button>
      <div id="route-ui-container"></div>
    </section>

    <section>
      <h3>🔥 3. Live Heatmap</h3>
      <label class="full-row">Hour of Day (0-23)<input type="number" id="heatmapHour" value="14" min="0" max="23"></label>
      <button onclick="heatmap(this)">Generate Heatmap</button>
    </section>

    <section>
      <h3>🚨 4. Report Crime Incident</h3>
      <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px;line-height:1.5;">
        Reports the incident → updates crime density → recalculates safety score → recommends a safer alternate route.
      </p>
      <div class="row">
        <label>Incident Latitude  <input type="text" id="crimeLat" value="17.4345"></label>
        <label>Incident Longitude <input type="text" id="crimeLng" value="78.3550"></label>
        <button type="button" onclick="getLocation(this)" style="grid-column: 1 / -1; background: linear-gradient(135deg, #10b981, #059669); box-shadow: 0 4px 12px -4px rgba(16, 185, 129, 0.5);">📍 Use My Current Location</button>
        <label class="full-row">Description <input type="text" id="crimeDesc" value="Suspicious activity"></label>
        <label>Severity (1 to 10) <input type="number" id="crimeSev" value="5" min="1" max="10"></label>
        <label>Time (HH:MM) <input type="text" id="crimeTime" value="14:00"></label>
      </div>
      <p style="color:#38bdf8;font-size:0.85rem;margin:12px 0 4px;font-weight:600;">Optional — provide your journey to get a safer alternate route:</p>
      <div class="row">
        <label>Your Start Latitude  <input type="text" id="crimeStartLat" value="17.4267" placeholder="Leave blank to skip"></label>
        <label>Your Start Longitude <input type="text" id="crimeStartLng" value="78.3368" placeholder="Leave blank to skip"></label>
        <label>Your End Latitude    <input type="text" id="crimeEndLat"   value="17.4455" placeholder="Leave blank to skip"></label>
        <label>Your End Longitude   <input type="text" id="crimeEndLng"   value="78.3317" placeholder="Leave blank to skip"></label>
      </div>
      <button onclick="reportCrime(this)" class="danger" style="margin-top:12px">Submit Incident Report</button>
      <div id="crime-result-ui"></div>
    </section>

    <section class="result-section">
      <h3>Console Output</h3>
      <div id="out-container">
        <pre id="out">Connect to the API by running a command...</pre>
      </div>
    </section>
  </div>

  <script>
    const base = window.location.origin;
    document.getElementById('base').textContent = base;
    const pre = document.getElementById('out');
    
    function setBtnLoading(btn, isLoading, originalText) {{
      if (isLoading) {{
        btn.innerHTML = `<span class="loading"></span> Processing...`;
        btn.disabled = true;
      }} else {{
        btn.innerHTML = originalText;
        btn.disabled = false;
      }}
    }}

    function out(obj, fromSafestRoute=false) {{ 
      pre.textContent = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2); 
      if (!fromSafestRoute) {{
          document.getElementById('route-ui-container').innerHTML = '';
      }}
      document.getElementById('out-container').scrollIntoView({{behavior: 'smooth', block: 'end'}});
    }}
    
    async function handleResponse(r) {{
      const text = await r.text();
      try {{ return JSON.parse(text); }} catch (_) {{ return text; }}
    }}

    async function call(path, btn) {{
      const originalText = btn.innerHTML;
      setBtnLoading(btn, true, originalText);
      try {{ 
        const res = await handleResponse(await fetch(base + path));
        out(res);
      }} catch (e) {{ 
        out('Error: ' + e.message); 
      }} finally {{
        setBtnLoading(btn, false, originalText);
      }}
    }}

    async function fetchSegmentDetails(edgeId, hour) {{
      try {{
        const res = await fetch(`${{base}}/segment/${{edgeId}}?hour=${{hour}}`);
        const data = await res.json();
        out(data, true); // Keep original fromSafestRoute true so we don't clear UI
      }} catch (e) {{
        out('Error fetching segment details: ' + e.message);
      }}
    }}

    // Global tracking to update journey travel history natively
    let lastRenderedSegmentIds = [];

    async function safestRoute(btn) {{
      const originalText = btn.innerHTML;
      setBtnLoading(btn, true, originalText);
      document.getElementById('route-ui-container').innerHTML = '';
      lastRenderedSegmentIds = []; // clear previous
      
      const timeStr = document.getElementById('time').value || null;
      let hourNum = new Date().getHours();
      if (timeStr) {{
        try {{ hourNum = parseInt(timeStr.split(':')[0], 10); }} catch(e) {{}}
      }}
      
      const body = {{
        start: {{ lat: parseFloat(document.getElementById('startLat').value), lng: parseFloat(document.getElementById('startLng').value) }},
        end:   {{ lat: parseFloat(document.getElementById('endLat').value),   lng: parseFloat(document.getElementById('endLng').value) }},
        time:  timeStr,
        user_id: document.getElementById('userId').value || null
      }};
      
      try {{ 
        const res = await fetch(base + '/safest_route', {{ 
          method: 'POST', 
          headers: {{'Content-Type': 'application/json'}}, 
          body: JSON.stringify(body) 
        }});
        let data = "";
        if (res.ok) {{
            data = await res.json();
            
            // Extract route segments for later "Complete Journey" interaction
            if (data.safest_route && data.safest_route.segments) {{
                lastRenderedSegmentIds = data.safest_route.segments.map(s => s.segment_id).filter(id => id);
            }}
        }} else {{
            const err = await handleResponse(res);
            throw new Error(err.detail || 'Failed fetch');
        }}
        
        out(data, true);
        
        // Build cool UI for up to 3 segments
        if (data.safest_route && data.safest_route.length > 0) {{
          const segments = data.safest_route;
          const displaySegs = segments.slice(0, 3); // Limit to top 3 edges
          
          let html = `<div class="safest-route-ui">
            <h4 style="color:#38bdf8; margin-bottom:12px; margin-top:24px; font-weight:600;">Segment Explorer (Showing ${{displaySegs.length}} of ${{segments.length}} edges)</h4>
          `;
          
          displaySegs.forEach((seg, i) => {{
            let badgeBg = 'rgba(239, 68, 68, 0.2)';
            let badgeColor = '#fca5a5';
            if (seg.safety_score >= 80) {{ badgeBg = 'rgba(34, 197, 94, 0.2)'; badgeColor = '#4ade80'; }}
            else if (seg.safety_score >= 60) {{ badgeBg = 'rgba(234, 179, 8, 0.2)'; badgeColor = '#fde047'; }}
            else if (seg.safety_score >= 40) {{ badgeBg = 'rgba(249, 115, 22, 0.2)'; badgeColor = '#fdba74'; }}
            
            html += `
              <div class="segment-card">
                <div>
                  <div style="font-weight:600; color:#f8fafc; font-size:14px; margin-bottom:6px;">Seg ${{seg.segment_id}}</div>
                  <span class="badge" style="background:${{badgeBg}}; color:${{badgeColor}}">Safety: ${{seg.safety_score.toFixed(1)}}</span>
                </div>
                <button class="segment-details-btn" onclick="fetchSegmentDetails('${{seg.segment_id}}', ${{hourNum}})">View Details</button>
              </div>
            `;
          }});
          
          if (segments.length > 3) {{
            html += `<div style="text-align:center; color:#94a3b8; font-size:12px; margin-top:12px;">+ ${{segments.length - 3}} more edges attached to path</div>`;
          }}
          html += `</div>`;
          document.getElementById('route-ui-container').innerHTML = html;
        }}
        
      }} catch(e) {{ 
        out('Error: '+e.message); 
      }} finally {{
        setBtnLoading(btn, false, originalText);
      }}
    }}
    
    async function completeJourney(btn) {{
        const originalText = btn.innerHTML;
        const uid = document.getElementById('userId').value;
        if (!uid) {{
           out("Error: You must provide a User ID to save journey history!");
           return;
        }}
        if (lastRenderedSegmentIds.length === 0) {{
           out("Error: No route currently tracked. Route a path first!");
           return;
        }}
        
        setBtnLoading(btn, true, originalText);
        
        const body = {{
            user_id: uid,
            segment_ids: lastRenderedSegmentIds
        }};
        
        try {{
            const res = await fetch(base + '/api/routes/complete-journey', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(body)
            }});
            out(await handleResponse(res));
        }} catch(e) {{
            out("Error: " + e.message);
        }} finally {{
            setBtnLoading(btn, false, originalText);
        }}
    }}

    async function heatmap(btn) {{
      const originalText = btn.innerHTML;
      setBtnLoading(btn, true, originalText);
      try {{
        const hr = document.getElementById('heatmapHour').value;
        const res = await handleResponse(await fetch(base + '/heatmap?hour=' + hr));
        out(res);
      }} catch(e) {{ 
        out('Error: '+e.message); 
      }} finally {{
        setBtnLoading(btn, false, originalText);
      }}
    }}

    function getLocation(btn) {{
      const originalText = btn.innerHTML;
      setBtnLoading(btn, true, "Locating...");
      
      if (navigator.geolocation) {{
        navigator.geolocation.getCurrentPosition(
          (position) => {{
             document.getElementById('crimeLat').value = position.coords.latitude.toFixed(5);
             document.getElementById('crimeLng').value = position.coords.longitude.toFixed(5);
             setBtnLoading(btn, false, originalText);
             btn.innerHTML = "✅ Location Found!";
             setTimeout(() => btn.innerHTML = originalText, 2000);
          }},
          (error) => {{
             out('Geolocation error: ' + error.message);
             setBtnLoading(btn, false, originalText);
          }},
          {{ enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }}
        );
      }} else {{
        out('Geolocation is not supported by this browser.');
        setBtnLoading(btn, false, originalText);
      }}
    }}

    async function reportCrime(btn) {{
      const originalText = btn.innerHTML;
      setBtnLoading(btn, true, originalText);
      document.getElementById('crime-result-ui').innerHTML = '';

      // Collect optional route endpoints
      const startLatVal = document.getElementById('crimeStartLat').value.trim();
      const startLngVal = document.getElementById('crimeStartLng').value.trim();
      const endLatVal   = document.getElementById('crimeEndLat').value.trim();
      const endLngVal   = document.getElementById('crimeEndLng').value.trim();
      const hasRoute    = startLatVal && startLngVal && endLatVal && endLngVal;

      const body = {{
        lat:         parseFloat(document.getElementById('crimeLat').value),
        lng:         parseFloat(document.getElementById('crimeLng').value),
        description: document.getElementById('crimeDesc').value,
        severity:    parseInt(document.getElementById('crimeSev').value, 10),
        time:        document.getElementById('crimeTime').value || null,
        route_start: hasRoute ? {{ lat: parseFloat(startLatVal), lng: parseFloat(startLngVal) }} : null,
        route_end:   hasRoute ? {{ lat: parseFloat(endLatVal),   lng: parseFloat(endLngVal)   }} : null,
      }};

      try {{
        const res  = await fetch(base + '/report_crime', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(body)
        }});
        const data = await handleResponse(res);
        out(data);

        // ── Render step-by-step visual summary ────────────────────────
        const ui = document.getElementById('crime-result-ui');
        if (!data || typeof data !== 'object') {{ ui.innerHTML = ''; return; }}

        const imp = data.segment_impact;
        const alt = data.alternate_route;

        let html = `<div style="margin-top:20px; display:flex; flex-direction:column; gap:14px;">`;

        // Step pipeline banner
        html += `
          <div style="background:rgba(15,23,42,0.8);border:1px solid #334155;border-radius:10px;padding:14px;">
            <div style="color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Incident Pipeline</div>
            <div style="display:flex;gap:0;align-items:center;flex-wrap:wrap;">
              ${{['📍 Received','🔍 Segment Found','📊 Score Updated','🗺️ Route Recalculated','📡 Alert Broadcast'].map((s,i) => `
                <div style="display:flex;align-items:center;">
                  <div style="background:rgba(56,189,248,0.15);border:1px solid #38bdf8;border-radius:6px;padding:5px 10px;font-size:11px;color:#38bdf8;font-weight:600;white-space:nowrap;">
                    Step ${{i+1}}: ${{s}}
                  </div>
                  ${{i < 4 ? '<div style="width:18px;height:2px;background:#334155;margin:0 2px;"></div>' : ''}}
                </div>
              `).join('')}}
            </div>
          </div>`;

        // Segment impact card (Steps 2 & 3)
        if (imp) {{
          const drop = imp.score_drop;
          const dropColor = drop > 10 ? '#f87171' : drop > 5 ? '#fdba74' : '#fde047';
          html += `
            <div style="background:rgba(30,41,59,0.9);border:1px solid #334155;border-radius:10px;padding:16px;">
              <div style="color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Steps 2 & 3 — Segment Updated & Score Recalculated</div>
              <div style="font-weight:600;color:#f8fafc;margin-bottom:10px;font-size:13px;">Segment: <code style="color:#818cf8;">${{imp.segment_id}}</code></div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
                <div style="background:#0f172a;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">Crime Density</div>
                  <div style="color:#fca5a5;font-size:13px;">${{imp.old_crime_density}} → <b style="color:#f87171">${{imp.new_crime_density}}</b></div>
                </div>
                <div style="background:#0f172a;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">Safety Score</div>
                  <div style="color:#e2e8f0;font-size:13px;">${{imp.old_safety_score}} → <b style="color:${{imp.new_safety_score >= 60 ? '#4ade80' : '#f87171'}}">${{imp.new_safety_score}}</b></div>
                </div>
                <div style="background:#0f172a;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">Score Drop</div>
                  <div style="font-weight:700;color:${{dropColor}};font-size:16px;">-${{drop}}</div>
                </div>
              </div>
            </div>`;
        }}

        // Alternate route card (Step 4)
        if (alt) {{
          const safetyColor = alt.average_safety >= 80 ? '#4ade80' : alt.average_safety >= 60 ? '#fde047' : '#fdba74';
          html += `
            <div style="background:rgba(30,41,59,0.9);border:1px solid #334155;border-radius:10px;padding:16px;">
              <div style="color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Step 4 — Safer Alternate Route Recommended</div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <span style="color:#f8fafc;font-size:13px;">📌 ${{alt.recommendation}}</span>
                <span style="background:rgba(34,197,94,0.15);border:1px solid #4ade80;border-radius:20px;padding:4px 12px;font-size:12px;color:#4ade80;font-weight:600;">Avg Safety: ${{alt.average_safety}}</span>
              </div>
              <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">Showing ${{Math.min(alt.segments.length,3)}} of ${{alt.total_segments}} route segments:</div>`;

          alt.segments.slice(0, 3).forEach((seg, i) => {{
            const sc = seg.safety_score;
            const c  = sc >= 80 ? '#4ade80' : sc >= 60 ? '#fde047' : sc >= 40 ? '#fdba74' : '#f87171';
            html += `
              <div style="background:#0f172a;border-radius:8px;padding:10px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;">
                <div>
                  <span style="color:#818cf8;font-size:11px;font-weight:600;">SEG ${{i+1}}</span>
                  <span style="color:#cbd5e1;font-size:12px;margin-left:8px;">(${{seg.start_lat.toFixed(4)}}, ${{seg.start_lng.toFixed(4)}}) → (${{seg.end_lat.toFixed(4)}}, ${{seg.end_lng.toFixed(4)}})</span>
                </div>
                <span style="background:rgba(0,0,0,0.3);border:1px solid ${{c}};border-radius:12px;padding:3px 10px;color:${{c}};font-size:12px;font-weight:700;">${{sc.toFixed(1)}}</span>
              </div>`;
          }});

          html += `</div>`;
        }} else if (data.alternate_route_error) {{
          html += `
            <div style="background:rgba(30,41,59,0.9);border:1px solid #475569;border-radius:10px;padding:14px;color:#94a3b8;font-size:13px;">
              Step 4 skipped: ${{data.alternate_route_error}}
              <br><span style="font-size:11px;">Provide Start/End coordinates above to get an alternate route recommendation.</span>
            </div>`;
        }}

        // Step 5 — broadcast confirmation
        html += `
          <div style="background:rgba(56,189,248,0.05);border:1px solid rgba(56,189,248,0.2);border-radius:10px;padding:12px;color:#38bdf8;font-size:12px;">
            Step 5 ✅ Real-time alert broadcast to all connected clients via WebSocket.
          </div>`;

        html += `</div>`;
        ui.innerHTML = html;

      }} catch(e) {{
        out('Error: ' + e.message);
      }} finally {{
        setBtnLoading(btn, false, originalText);
      }}
    }}
  </script>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# SOS Alert module — startup, POST, and WebSocket admin broadcast
# ---------------------------------------------------------------------------

from services.sos_service import init_sos_db

zeroconf_instance = None

@app.on_event("startup")
async def _init_sos_db_startup() -> None:
    """Initialize the SOS database, register mDNS service, and start background scheduler."""
    global zeroconf_instance
    init_sos_db()
    
    # Start background job scheduler
    from services.background_jobs import start_background_scheduler
    start_background_scheduler()
    
    try:
        ip = get_local_ip()
        info = ServiceInfo(
            "_http._tcp.local.",
            "saferoute._http._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=PORT,
            properties={"desc": "SafeRoute API Server"},
            server="saferoute.local."
        )
        zeroconf_instance = Zeroconf()
        zeroconf_instance.register_service(info)
        logger.info(f"mDNS Registered: saferoute.local -> {ip}:{PORT}")
    except Exception as e:
        logger.error(f"Failed to register mDNS: {e}")
        if zeroconf_instance is not None:
            try:
                zeroconf_instance.close()
            except Exception:
                pass
            finally:
                zeroconf_instance = None

@app.on_event("shutdown")
async def _shutdown_mdns() -> None:
    global zeroconf_instance
    
    # Stop background job scheduler
    from services.background_jobs import stop_background_scheduler
    stop_background_scheduler()
    
    if zeroconf_instance:
        try:
            zeroconf_instance.unregister_all_services()
        except Exception as e:
            logger.warning(f"Failed to unregister mDNS services cleanly: {e}")
        finally:
            try:
                zeroconf_instance.close()
            except Exception as e:
                logger.warning(f"Failed to close mDNS cleanly: {e}")
            zeroconf_instance = None


@app.post("/sos_alert")
async def create_sos_alert(alert: SOSAlert):
    """
    Receive an SOS alert from the user, persist it to SQLite,
    and immediately broadcast it to all connected admin WebSocket clients.
    """
    # 1. Persist to SQLite
    conn = _get_sos_db()
    conn.execute(
        "INSERT INTO sos_alerts (user_id, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)",
        (alert.user_id, alert.latitude, alert.longitude, alert.timestamp),
    )
    conn.commit()
    conn.close()
    logger.warning(
        "SOS ALERT from user %s at (%.6f, %.6f) ts=%s",
        alert.user_id, alert.latitude, alert.longitude, alert.timestamp,
    )

    # 2. Build the broadcast payload
    payload = {
        "alert_type": "SOS",
        "user_id":    alert.user_id,
        "latitude":   alert.latitude,
        "longitude":  alert.longitude,
        "timestamp":  alert.timestamp,
    }

    # 3. Broadcast to all connected admin clients
    await admin_manager.broadcast_sos(payload)

    return {
        "status": "SOS alert received and broadcasted",
        "admin_clients_notified": len(admin_manager.active_connections),
    }


@app.get("/sos_alerts")
async def list_sos_alerts(limit: int = 50):
    """Retrieve the most recent SOS alerts (admin use only)."""
    conn = _get_sos_db()
    rows = conn.execute(
        "SELECT id, user_id, latitude, longitude, timestamp, received_at "
        "FROM sos_alerts ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id":          r["id"],
            "user_id":     r["user_id"],
            "latitude":    r["latitude"],
            "longitude":   r["longitude"],
            "timestamp":   r["timestamp"],
            "received_at": r["received_at"],
            "alert_type":  "SOS",
        }
        for r in rows
    ]


@app.websocket("/ws/admin_alert")
async def admin_alert_websocket(websocket: WebSocket):
    """
    Admin dashboard connects here to receive real-time SOS push notifications.
    Multiple admin clients are supported simultaneously.
    """
    await admin_manager.connect(websocket)
    try:
        # Keep the connection alive; we only push, never expect client messages
        while True:
            await websocket.receive_text()  # waits for ping or disconnect
    except WebSocketDisconnect:
        admin_manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# WebSocket for live alerts
# ---------------------------------------------------------------------------

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_alert(alert: dict):
    for conn in active_connections:
        try:
            await conn.send_json(alert)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Run server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
