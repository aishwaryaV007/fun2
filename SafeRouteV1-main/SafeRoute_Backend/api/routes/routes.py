"""
ai/api/routes/routes.py
========================
Canonical route endpoints for the unified SafeRoute AI backend.

Exposes the following clean, versioned URLs (in addition to legacy URLs
on ai/main.py which remain unchanged):

  POST /routes/safest   — safest path between two points
  POST /routes/fastest  — shortest-distance path between two points
  GET  /routes/score    — per-segment safety score heatmap

Both the mobile app and admin dashboard should prefer these canonical
endpoints. Legacy endpoints (/safest_route, /heatmap) on main.py stay
active for backward compatibility.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.config import (
    ADMIN_READ_RATE_LIMIT_REQUESTS,
    ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    BOUNDS,
    ROUTE_RATE_LIMIT_REQUESTS,
    ROUTE_RATE_LIMIT_WINDOW_SECONDS,
    coords_in_bounds,
    get_time_multiplier,
)
from core.security import require_admin_api_key_if_enabled
from services.rate_limiter import enforce_rate_limit
from services.route_service import build_route_response_summary
from services.safety_engine import calculate_safety_score, get_safety_color

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routes", tags=["Routes"])
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


# ---------------------------------------------------------------------------
# Shared Pydantic models (local copies to avoid circular import from main.py)
# ---------------------------------------------------------------------------

class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    start: Location
    end: Location
    time: Optional[str] = Field(default=None, max_length=5)       # HH:MM format
    user_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    force_fresh: bool = False

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None or TIME_PATTERN.fullmatch(value):
            return value
        raise ValueError("time must use HH:MM 24-hour format")


# ---------------------------------------------------------------------------
# Helper — import live data from main.py at *call time*, not at import time.
# This avoids circular imports while still reading the authoritative
# ROAD_SEGMENTS list that is mutated by crime reports during the server session.
# ---------------------------------------------------------------------------

def _get_main_state():
    """Return references to the live objects in ai/main.py."""
    import main as _main  # noqa: PLC0415
    return (
        _main.ROAD_SEGMENTS,
        _main.route_cache,
        _main.build_road_graph,
        _main.find_nearest_node,
        _main.calculate_route,
        _main.FamiliarityScoreCalculator,
        _main.get_db,
    )


# ---------------------------------------------------------------------------
# POST /routes/safest
# ---------------------------------------------------------------------------

@router.post("/safest", summary="Calculate the safest route between two points")
async def get_safest_route_canonical(route_request: RouteRequest, http_request: Request):
    """
    Canonical alias for POST /safest_route.

    Returns both the safest (risk-minimising) and shortest (fastest) paths
    so the client can present a route-choice UI.
    """
    enforce_rate_limit(
        http_request,
        scope="routes.safest",
        limit=ROUTE_RATE_LIMIT_REQUESTS,
        window_seconds=ROUTE_RATE_LIMIT_WINDOW_SECONDS,
        subject=route_request.user_id,
    )

    # Bounds validation
    if not coords_in_bounds(route_request.start.lat, route_request.start.lng):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Start coordinates ({route_request.start.lat}, {route_request.start.lng}) "
                f"are outside the supported area. "
                f"Bounds: lat [{BOUNDS['min_lat']}, {BOUNDS['max_lat']}], "
                f"lng [{BOUNDS['min_lng']}, {BOUNDS['max_lng']}]"
            ),
        )
    if not coords_in_bounds(route_request.end.lat, route_request.end.lng):
        raise HTTPException(
            status_code=400,
            detail=f"End coordinates ({route_request.end.lat}, {route_request.end.lng}) are outside the supported area.",
        )

    # Parse hour
    if route_request.time:
        try:
            hour = int(route_request.time.split(":")[0])
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    else:
        hour = datetime.now().hour

    (
        ROAD_SEGMENTS, route_cache, build_road_graph,
        find_nearest_node, calculate_route,
        FamiliarityScoreCalculator, get_db,
    ) = _get_main_state()

    # Check cache
    cache_key = (
        f"{route_request.start.lat}_{route_request.start.lng}"
        f"_{route_request.end.lat}_{route_request.end.lng}"
        f"_{hour}_{route_request.user_id}_canonical"
    )

    # Try TTL-aware cache (admin backend style) or plain dict (ai/main.py style)
    cached = route_cache.get(cache_key) if hasattr(route_cache, "get") else route_cache.get(cache_key)
    if cached and not route_request.force_fresh:
        return cached

    # Familiarity map
    familiarity_map: dict[str, float] = {}
    if route_request.user_id:
        all_segment_ids = [s.get("segment_id", "") for s in ROAD_SEGMENTS if s.get("segment_id")]
        try:
            from services.familiarity_module import get_db as _get_db  # noqa: PLC0415
            db = next(_get_db())
            fam_resp = FamiliarityScoreCalculator.calculate_route_familiarity(
                user_id=route_request.user_id, segment_ids=all_segment_ids, db=db
            )
            familiarity_map = {seg.segment_id: seg.familiarity_score for seg in fam_resp.segments}
            db.close()
        except Exception as e:
            logger.warning("Familiarity lookup failed for user %s: %s", route_request.user_id, e)

    # Build graph
    result_tuple = build_road_graph(hour, familiarity_map=familiarity_map)
    # build_road_graph may return (G,) or (G, tree, node_list)
    if isinstance(result_tuple, tuple) and len(result_tuple) == 3:
        G, node_tree, node_list = result_tuple
    else:
        G = result_tuple
        node_tree, node_list = None, None

    start_node = find_nearest_node(
        G,
        route_request.start.lat,
        route_request.start.lng,
        node_tree,
        node_list,
    )
    end_node = find_nearest_node(
        G,
        route_request.end.lat,
        route_request.end.lng,
        node_tree,
        node_list,
    )

    if not start_node or not end_node:
        raise HTTPException(status_code=400, detail="Could not find route nodes")
    if start_node == end_node:
        raise HTTPException(
            status_code=400,
            detail=(
                "Start and end resolve to the same node. "
                "The dataset covers the Gachibowli / HITEC City area "
                "(lat 17.42–17.46, lng 78.32–78.37)."
            ),
        )

    safest_route  = calculate_route(G, start_node, end_node, use_safety=True)
    fastest_route = calculate_route(G, start_node, end_node, use_safety=False)

    if not safest_route:
        raise HTTPException(status_code=404, detail="No route found")

    result = {
        "safest_route":  safest_route,
        "shortest_route": fastest_route,
        "time_of_day":   f"{hour}:00",
        "time_multiplier": get_time_multiplier(hour),
        "mode": "safest",
        "cached": False,
        **build_route_response_summary(safest_route),
    }

    # Store in cache
    if hasattr(route_cache, "set"):
        route_cache.set(cache_key, {**result, "cached": True})
    else:
        route_cache[cache_key] = {**result, "cached": True}

    return result


# ---------------------------------------------------------------------------
# POST /routes/fastest
# ---------------------------------------------------------------------------

@router.post("/fastest", summary="Calculate the fastest (shortest-distance) route")
async def get_fastest_route(route_request: RouteRequest, http_request: Request):
    """
    Returns the shortest-distance path without safety optimisation.
    Shares all validation and graph-building logic with /routes/safest.
    """
    # Bounds check
    for coord, name in [
        ((route_request.start.lat, route_request.start.lng), "Start"),
        ((route_request.end.lat,   route_request.end.lng),   "End"),
    ]:
        if not coords_in_bounds(*coord):
            raise HTTPException(
                status_code=400,
                detail=f"{name} coordinates {coord} are outside the supported area.",
            )

    enforce_rate_limit(
        http_request,
        scope="routes.fastest",
        limit=ROUTE_RATE_LIMIT_REQUESTS,
        window_seconds=ROUTE_RATE_LIMIT_WINDOW_SECONDS,
        subject=route_request.user_id,
    )

    hour = datetime.now().hour
    if route_request.time:
        try:
            hour = int(route_request.time.split(":")[0])
        except (ValueError, IndexError):
            pass

    (_, _, build_road_graph, find_nearest_node, calculate_route, _, _) = _get_main_state()

    result_tuple = build_road_graph(hour)
    if isinstance(result_tuple, tuple) and len(result_tuple) == 3:
        G, node_tree, node_list = result_tuple
    else:
        G = result_tuple
        node_tree, node_list = None, None

    start_node = find_nearest_node(
        G,
        route_request.start.lat,
        route_request.start.lng,
        node_tree,
        node_list,
    )
    end_node = find_nearest_node(
        G,
        route_request.end.lat,
        route_request.end.lng,
        node_tree,
        node_list,
    )

    if not start_node or not end_node or start_node == end_node:
        raise HTTPException(status_code=400, detail="Could not resolve route nodes")

    fastest = calculate_route(G, start_node, end_node, use_safety=False)
    if not fastest:
        raise HTTPException(status_code=404, detail="No route found")

    return {
        "fastest_route":  fastest,
        "time_of_day":    f"{hour}:00",
        "time_multiplier": get_time_multiplier(hour),
        "mode":           "fastest",
        **build_route_response_summary(fastest),
    }


# ---------------------------------------------------------------------------
# GET /routes/score
# ---------------------------------------------------------------------------

@router.get("/score", summary="Per-segment safety score heatmap")
async def get_route_score(
    http_request: Request,
    hour: Optional[int] = Query(default=None, ge=0, le=23),
    _: str | None = Depends(require_admin_api_key_if_enabled),
):
    """
    Returns a safety score for every road segment in the grid.
    Canonical alias for GET /heatmap.
    """
    if hour is None:
        hour = datetime.now().hour

    enforce_rate_limit(
        http_request,
        scope="routes.score",
        limit=ADMIN_READ_RATE_LIMIT_REQUESTS,
        window_seconds=ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    )

    ROAD_SEGMENTS, *_ = _get_main_state()

    heatmap_data = []
    for seg in ROAD_SEGMENTS:
        safety, impacts = calculate_safety_score(seg, hour)
        heatmap_data.append({
            "edge_id":    seg["edge_id"],
            "segment_id": seg.get("segment_id", ""),
            "start": {
                "lat": seg.get("start_lat", seg.get("start", (0.0, 0.0))[0]),
                "lng": seg.get("start_lon", seg.get("start", (0.0, 0.0))[1]),
            },
            "end": {
                "lat": seg.get("end_lat", seg.get("end", (0.0, 0.0))[0]),
                "lng": seg.get("end_lon", seg.get("end", (0.0, 0.0))[1]),
            },
            "safety_score": safety,
            "impacts":    impacts,
            "color":      get_safety_color(safety),
            "road_type":  seg.get("road_type", "unknown"),
        })

    return {
        "hour":            hour,
        "time_multiplier": get_time_multiplier(hour),
        "total_segments":  len(heatmap_data),
        "segments":        heatmap_data,
        "legend": {
            "green":  "80-100 (Safe)",
            "yellow": "60-79  (Caution)",
            "orange": "40-59  (Risky)",
            "red":    "0-39   (Danger)",
        },
    }


# ---------------------------------------------------------------------------
# OSM-based routing endpoints (Real Hyderabad Road Network)
# ---------------------------------------------------------------------------

@router.post(
    "/osm/safest",
    summary="Safest route using real OSM road network",
    description="Uses actual OpenStreetMap data for Gachibowli, Hyderabad"
)
async def get_osm_safest_route(request: RouteRequest, http_request: Request):
    """
    Calculate the safest route using real OpenStreetMap road network data.
    
    This endpoint uses actual road network extracted from OSM for the
    Gachibowli area, including real junction positions and road connectivity.
    
    Returns the safest path that maximizes safety metrics.
    """
    from services.route_service import calculate_osm_safest_route

    enforce_rate_limit(
        http_request,
        scope="routes.osm.safest",
        limit=ROUTE_RATE_LIMIT_REQUESTS,
        window_seconds=ROUTE_RATE_LIMIT_WINDOW_SECONDS,
        subject=request.user_id,
    )
    
    # Validate coordinates
    if not coords_in_bounds(request.start.lat, request.start.lng):
        raise HTTPException(
            status_code=400,
            detail=f"Start coordinates are outside supported area",
        )
    if not coords_in_bounds(request.end.lat, request.end.lng):
        raise HTTPException(
            status_code=400,
            detail=f"End coordinates are outside supported area",
        )
    
    try:
        result = calculate_osm_safest_route(
            request.start.lat,
            request.start.lng,
            request.end.lat,
            request.end.lng,
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail=result.get("status", "Route calculation failed")
            )
        
        return result
        
    except Exception as e:
        logger.error("OSM safest route error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/osm/shortest",
    summary="Shortest route using real OSM road network",
    description="Uses actual OpenStreetMap data for Gachibowli, Hyderabad"
)
async def get_osm_shortest_route(request: RouteRequest, http_request: Request):
    """
    Calculate the shortest (distance-optimized) route using real OSM data.
    
    Prioritizes distance over safety, returns the quickest path.
    """
    from services.route_service import calculate_osm_shortest_route

    enforce_rate_limit(
        http_request,
        scope="routes.osm.shortest",
        limit=ROUTE_RATE_LIMIT_REQUESTS,
        window_seconds=ROUTE_RATE_LIMIT_WINDOW_SECONDS,
        subject=request.user_id,
    )
    
    # Validate coordinates
    if not coords_in_bounds(request.start.lat, request.start.lng):
        raise HTTPException(
            status_code=400,
            detail=f"Start coordinates are outside supported area",
        )
    if not coords_in_bounds(request.end.lat, request.end.lng):
        raise HTTPException(
            status_code=400,
            detail=f"End coordinates are outside supported area",
        )
    
    try:
        result = calculate_osm_shortest_route(
            request.start.lat,
            request.start.lng,
            request.end.lat,
            request.end.lng,
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail=result.get("status", "Route calculation failed")
            )
        
        return result
        
    except Exception as e:
        logger.error("OSM shortest route error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/osm/balanced",
    summary="Balanced route using real OSM road network",
    description="Balances safety and distance using actual OpenStreetMap data"
)
async def get_osm_balanced_route(
    request: RouteRequest,
    http_request: Request,
    safety_weight: float = Query(default=0.6, ge=0.0, le=1.0),
):
    """
    Calculate a balanced route between safety and distance.
    
    Parameters:
        safety_weight: 0.0-1.0, default 0.6 (60% safety, 40% distance)
    """
    from services.route_service import calculate_osm_balanced_route

    enforce_rate_limit(
        http_request,
        scope="routes.osm.balanced",
        limit=ROUTE_RATE_LIMIT_REQUESTS,
        window_seconds=ROUTE_RATE_LIMIT_WINDOW_SECONDS,
        subject=request.user_id,
    )
    
    # Validate coordinates
    if not coords_in_bounds(request.start.lat, request.start.lng):
        raise HTTPException(
            status_code=400,
            detail=f"Start coordinates are outside supported area",
        )
    if not coords_in_bounds(request.end.lat, request.end.lng):
        raise HTTPException(
            status_code=400,
            detail=f"End coordinates are outside supported area",
        )
    
    try:
        result = calculate_osm_balanced_route(
            request.start.lat,
            request.start.lng,
            request.end.lat,
            request.end.lng,
            safety_weight=safety_weight,
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail=result.get("status", "Route calculation failed")
            )
        
        return result
        
    except Exception as e:
        logger.error("OSM balanced route error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# AI Safety Analysis Endpoints
# ---------------------------------------------------------------------------

@router.get("/heatmap", tags=["Safety Analysis"])
async def get_crime_heatmap(
    http_request: Request,
    _: str | None = Depends(require_admin_api_key_if_enabled),
):
    """
    Get crime density heatmap for the Gachibowli area.
    
    Returns grid cells with crime density weights (0-1).
    Used by admin dashboard to visualize high-crime areas.
    
    Response:
    --------
    [
        {
            "latitude": 17.4435,
            "longitude": 78.3484,
            "weight": 0.85
        }
    ]
    """
    from services.crime_heatmap_service import get_heatmap_service

    enforce_rate_limit(
        http_request,
        scope="routes.heatmap",
        limit=ADMIN_READ_RATE_LIMIT_REQUESTS,
        window_seconds=ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    )
    
    try:
        heatmap_service = get_heatmap_service()
        heatmap = heatmap_service.get_heatmap()
        return {
            "status": "success",
            "count": len(heatmap),
            "heatmap": heatmap
        }
    except Exception as e:
        logger.error("Heatmap generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/danger-zones", tags=["Safety Analysis"])
async def get_danger_zones(
    http_request: Request,
    _: str | None = Depends(require_admin_api_key_if_enabled),
):
    """
    Get detected danger zones (clusters of high crime).
    
    Uses DBSCAN clustering to group nearby crimes.
    Returns zones with center, radius, and risk score.
    
    Used by admin dashboard to draw red circles around dangerous areas.
    
    Response:
    --------
    [
        {
            "lat": 17.4435,
            "lng": 78.3484,
            "radius": 0.005,
            "risk_score": 0.92
        }
    ]
    """
    from services.danger_zone_detector import get_danger_zone_detector

    enforce_rate_limit(
        http_request,
        scope="routes.danger_zones",
        limit=ADMIN_READ_RATE_LIMIT_REQUESTS,
        window_seconds=ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS,
    )
    
    try:
        detector = get_danger_zone_detector()
        zones = detector.detect_danger_zones()
        return {
            "status": "success",
            "count": len(zones),
            "danger_zones": zones
        }
    except Exception as e:
        logger.error("Danger zone detection error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
