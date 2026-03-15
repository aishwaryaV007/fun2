"""
Safety Config — Shared constants for the Women Safety Route Predictor
=====================================================================
Single source of truth for weights, normalization caps, coordinate
bounds, Gachibowli center, and environment-driven settings.

Coverage Area: 5 km radius around Gachibowli, Hyderabad
Center:        17.4435°N, 78.3484°E
"""

from __future__ import annotations

import math
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# API authentication
# ---------------------------------------------------------------------------
API_KEY: str = os.getenv("SAFETY_API_KEY", "dev-key-change-in-production")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./safe_routes.db",
)

# ---------------------------------------------------------------------------
# Safety score weights  (sum = 1.0)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "crime":       0.40,  # Highest
    "cctv":        0.20,  # Moderate
    "lighting":    0.20,  # Moderate
    "familiarity": 0.10,  # Lower
    "road_type":   0.10,  # Lower
}

# ---------------------------------------------------------------------------
# Normalization Anchors (Saturation Points)
# ---------------------------------------------------------------------------
MAX_VALUES = {
    "crime":    2.0,    # Max normalized density
    "cctv":     5.0,    # Saturation point for safety benefit
    "crowd":    100.0,  # High-traffic hub threshold
    "vibrancy": 5.0,    # Nearby shops/places count for community safety
}

# ---------------------------------------------------------------------------
# Gachibowli Center — primary coverage anchor
# ---------------------------------------------------------------------------
GACHIBOWLI_CENTER = {
    "latitude":  17.4435,
    "longitude": 78.3484,
    "name":      "Gachibowli",
}

# ---------------------------------------------------------------------------
# Coverage radius — 5 km around Gachibowli
# ---------------------------------------------------------------------------
COVERAGE_RADIUS_METERS: int = 5000  # 5 km

# ---------------------------------------------------------------------------
# Coordinate bounding box — Gachibowli-centered 5 km radius
#
# Degree conversions at latitude ~17°:
#   1 degree latitude  ≈ 111,000 m  →  5000 m ≈ 0.04505°
#   1 degree longitude ≈ 106,000 m  →  5000 m ≈ 0.04717°
# ---------------------------------------------------------------------------
_LAT_DEG_PER_METER = 1 / 111_000          # ~0.000009009
_LNG_DEG_PER_METER = 1 / 106_000          # ~0.000009434  (at ~17° latitude)

_lat_offset = COVERAGE_RADIUS_METERS * _LAT_DEG_PER_METER   # ≈ 0.04505
_lng_offset = COVERAGE_RADIUS_METERS * _LNG_DEG_PER_METER   # ≈ 0.04717

BOUNDS = {
    # Rectangular envelope for fast pre-filter
    "min_lat": round(GACHIBOWLI_CENTER["latitude"]  - _lat_offset, 6),  # ~17.3985
    "max_lat": round(GACHIBOWLI_CENTER["latitude"]  + _lat_offset, 6),  # ~17.4886
    "min_lng": round(GACHIBOWLI_CENTER["longitude"] - _lng_offset, 6),  # ~78.3012
    "max_lng": round(GACHIBOWLI_CENTER["longitude"] + _lng_offset, 6),  # ~78.3956

    # Center reference (kept inside BOUNDS for convenience)
    "center_lat":     GACHIBOWLI_CENTER["latitude"],
    "center_lng":     GACHIBOWLI_CENTER["longitude"],
    "radius_meters":  COVERAGE_RADIUS_METERS,
}

# ---------------------------------------------------------------------------
# Junction configuration
# ---------------------------------------------------------------------------
JUNCTION_CONFIG = {
    "min_connecting_roads": 2,      # Minimum roads to qualify as a junction
    "merge_distance_meters": 50,    # Merge junctions closer than this
    "endpoint_as_junction": True,   # Treat dead-ends as junctions too
}

# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance in **meters** between two GPS points
    using the Haversine formula.

    Parameters
    ----------
    lat1, lng1 : float  – first point (degrees)
    lat2, lng2 : float  – second point (degrees)

    Returns
    -------
    float
        Distance in meters.

    Example
    -------
    >>> haversine_distance(17.4435, 78.3484, 17.4500, 78.3550)
    # ≈ 893 m
    """
    R = 6_371_000.0  # Earth radius in metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# ---------------------------------------------------------------------------
# Radius check
# ---------------------------------------------------------------------------

def is_within_radius(
    lat: float,
    lng: float,
    center_lat: float = GACHIBOWLI_CENTER["latitude"],
    center_lng: float = GACHIBOWLI_CENTER["longitude"],
    radius_meters: float = COVERAGE_RADIUS_METERS,
) -> bool:
    """
    Return True if (lat, lng) is within *radius_meters* of the given centre.

    Defaults to checking against Gachibowli centre + 5 km radius.
    """
    return haversine_distance(lat, lng, center_lat, center_lng) <= radius_meters


# ---------------------------------------------------------------------------
# Coordinate validation (rectangular pre-filter + circular fine-check)
# ---------------------------------------------------------------------------

def coords_in_bounds(lat: float, lng: float) -> bool:
    """
    Return True if (lat, lng) falls within the supported grid area.

    Two-stage check:
      1. Fast rectangular bounds check (BOUNDS min/max lat/lng).
      2. Accurate circular check — must be within COVERAGE_RADIUS_METERS
         of GACHIBOWLI_CENTER using the Haversine formula.
    """
    # Stage 1 — cheap rectangular filter
    if not (
        BOUNDS["min_lat"] <= lat <= BOUNDS["max_lat"]
        and BOUNDS["min_lng"] <= lng <= BOUNDS["max_lng"]
    ):
        return False

    # Stage 2 — accurate circular filter
    return is_within_radius(lat, lng)


# ---------------------------------------------------------------------------
# Coverage info
# ---------------------------------------------------------------------------

def get_coverage_info() -> dict:
    """
    Return a dictionary describing the current coverage area.

    Useful for health-check endpoints and API documentation.
    """
    area_km2 = math.pi * (COVERAGE_RADIUS_METERS / 1000) ** 2

    return {
        "center": {
            "name":      GACHIBOWLI_CENTER["name"],
            "latitude":  GACHIBOWLI_CENTER["latitude"],
            "longitude": GACHIBOWLI_CENTER["longitude"],
        },
        "radius_meters":   COVERAGE_RADIUS_METERS,
        "radius_km":       COVERAGE_RADIUS_METERS / 1000,
        "area_km2":        round(area_km2, 2),
        "bounding_box": {
            "min_lat": BOUNDS["min_lat"],
            "max_lat": BOUNDS["max_lat"],
            "min_lng": BOUNDS["min_lng"],
            "max_lng": BOUNDS["max_lng"],
        },
    }


# ---------------------------------------------------------------------------
# Debug helper
# ---------------------------------------------------------------------------

def format_coordinate_debug(lat: float, lng: float) -> str:
    """
    Return a human-readable string with coordinates and their distance
    from the Gachibowli centre.

    Example output:
        "(17.4435, 78.3484) — 0.0 m from Gachibowli center [IN BOUNDS]"
    """
    dist = haversine_distance(
        lat, lng,
        GACHIBOWLI_CENTER["latitude"],
        GACHIBOWLI_CENTER["longitude"],
    )
    in_bounds = dist <= COVERAGE_RADIUS_METERS
    status = "IN BOUNDS" if in_bounds else "OUT OF BOUNDS"
    return (
        f"({lat}, {lng}) — {dist:.1f} m from {GACHIBOWLI_CENTER['name']} center [{status}]"
    )


# ---------------------------------------------------------------------------
# Time-of-day risk multiplier
# ---------------------------------------------------------------------------

def get_time_multiplier(hour: int) -> float:
    """
    Returns risk multiplier based on hour:
    Day (07:00-17:00): 1.0
    Dusk/Dawn (17:00-19:00, 05:00-07:00): 1.1
    Night (19:00-05:00): 1.3
    """
    if 7 <= hour < 17:
        return 1.0
    if (17 <= hour < 19) or (5 <= hour < 7):
        return 1.1
    return 1.3
