"""
SafeRoute Safety Score Engine with AI Enhancements
=================================================
Integrates heatmap weights and danger zones into road segment safety scoring.

New weights (per feedback):
- Crime density: 50%
- Lighting: 20%
- Crowd density: 15%
- CCTV coverage: 15%

Dynamic boosts:
- Heatmap cell weight → crime_density multiplier
- Danger zone proximity → additional risk penalty
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple, Optional
from pathlib import Path

from .crime_heatmap_service import get_heatmap_service
from .danger_zone_detector import get_danger_zone_detector

logger = logging.getLogger(__name__)

class SafetyScoreEngine:
    """
    Advanced safety scoring with heatmap and danger zone integration.
    """

    def __init__(self):
        self.heatmap_service = get_heatmap_service()
        self.danger_detector = get_danger_zone_detector()
        self.weights = {
            "crime": 0.5,
            "lighting": 0.2,
            "crowd": 0.15,
            "cctv": 0.15
        }

    def calculate_safety_score(
        self, 
        segment: Dict, 
        hour: int,
        familiarity_score: float = 0.2
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate enhanced safety score with dynamic boosts.
        """
        # Base factors (existing logic)
        crime_base = segment.get("crime_density", 0.0)
        cctv_norm = min(segment.get("cctv_count", 0) / 5.0, 1.0)  # Normalize
        lighting_norm = min(segment.get("lights_per_100m", 0.0) / 2.0, 1.0)
        crowd_norm = min(segment.get("crowd_density", 0.0) / 10.0, 1.0)
        fam_norm = 1.0 if familiarity_score > 0.3 else 0.5

        # AI Boost 1: Heatmap cell weight
        mid_lat = (segment.get("start_lat", 17.44) + segment.get("end_lat", 17.44)) / 2
        mid_lng = (segment.get("start_lon", 78.35) + segment.get("end_lon", 78.35)) / 2
        heatmap_boost = self.heatmap_service.get_cell_weight(mid_lat, mid_lng)
        effective_crime = crime_base + (heatmap_boost * 2.0)  # Scale boost

        # AI Boost 2: Danger zone penalty
        zones = self.danger_detector.detect_danger_zones()
        zone_penalty = 0.0
        for zone in zones:
            dist = haversine_distance(mid_lat, mid_lng, zone["center_lat"], zone["center_lng"])
            if dist < zone["radius_degrees"]:
                zone_penalty += zone["risk_score"] * (1.0 - dist / zone["radius_degrees"])
        effective_crime += zone_penalty

        # Weighted score
        impacts = {
            "crime_base": self.weights["crime"] * (1.0 - min(effective_crime, 1.0)) * 100,
            "lighting": self.weights["lighting"] * lighting_norm * 100,
            "crowd": self.weights["crowd"] * (1.0 - crowd_norm) * 100,
            "cctv": self.weights["cctv"] * cctv_norm * 100,
            "heatmap_boost": round(heatmap_boost * 20, 1),
            "zone_penalty": round(zone_penalty * 20, 1)
        }
        total = sum(impacts.values())
        score = max(0.0, min(100.0, total))
        return float(score), impacts

    def get_route_safety_multiplier(self, segments: list) -> float:
        """
        Compute overall route safety multiplier.
        """
        scores = [self.calculate_safety_score(seg, 12)[0] for seg in segments]
        avg = sum(scores) / len(scores)
        return 1.0 + (1.0 - avg / 100.0)  # 100% safe = 1.0x, 0% = 2.0x penalty

# Haversine utility
def haversine_distance(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0  # Earth radius km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # meters

# Global instance
_safety_engine: Optional[SafetyScoreEngine] = None

def get_safety_score_engine() -> SafetyScoreEngine:
    global _safety_engine
    if _safety_engine is None:
        _safety_engine = SafetyScoreEngine()
    return _safety_engine

