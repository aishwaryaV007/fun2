"""
ai/services/safety_engine.py
==============================
Safety scoring and utility functions, extracted from ai/main.py.

Provides:
  - DataNormalizationLayer  — normalise raw sensor counts to [0, 1]
  - calculate_safety_score()  — weighted multi-factor safety score
  - get_safety_color()        — colour band string for a score
  - get_unsafe_reasons()      — human-readable risk reasons

ai/main.py defines these too; this module is an independent re-export
intended for use by new api/routes/* modules and external consumers.
All logic is identical to what lives in ai/main.py — no behaviour change.
"""

from __future__ import annotations

from core.config import WEIGHTS, MAX_VALUES, get_time_multiplier

# Import the familiarity base score without pulling in main.py
try:
    from services.familiarity_module import FamiliarityScoreCalculator
    _FAM_BASE = FamiliarityScoreCalculator.BASE_SCORE
except Exception:
    _FAM_BASE = 0.2  # safe fallback


# ---------------------------------------------------------------------------
# Normalisation layer
# ---------------------------------------------------------------------------

class DataNormalizationLayer:
    """Standardises raw inputs into normalised 0–1 metrics."""

    @staticmethod
    def normalize_crime(density: float) -> float:
        return min(density / MAX_VALUES["crime"], 1.0)

    @staticmethod
    def normalize_cctv(count: int) -> float:
        return min(count / MAX_VALUES["cctv"], 1.0)

    @staticmethod
    def normalize_crowd(density: float) -> float:
        return min(density / MAX_VALUES["crowd"], 1.0)

    @staticmethod
    def normalize_vibrancy(safe_points: int) -> float:
        return min(safe_points / MAX_VALUES["vibrancy"], 1.0)


# ---------------------------------------------------------------------------
# Safety score
# ---------------------------------------------------------------------------

def calculate_safety_score(
    segment: dict,
    hour: int,
    familiarity_score: float = _FAM_BASE,
) -> tuple[float, dict[str, float]]:
    """
    Legacy wrapper → delegates to new SafetyScoreEngine.
    """
    from .safety_score_engine import get_safety_score_engine
    engine = get_safety_score_engine()
    return engine.calculate_safety_score(segment, hour, familiarity_score)

    time_mult = get_time_multiplier(hour)

    # CRIME (40 %)
    base_density  = segment.get("crime_density", 0.0)
    report_count  = segment.get("incident_report_count", 0)
    sev_avg       = segment.get("incident_severity_avg", 0.0)
    incident_boost = (sev_avg / 10.0) * min(report_count * 0.2, 1.0)
    raw_crime_risk = base_density + incident_boost
    effective_crime_risk = min(raw_crime_risk * time_mult, 2.0)
    crime_safety_norm = 1.0 - min(effective_crime_risk / 2.0, 1.0)

    # CCTV (20 %) + LIGHTING (20 %)
    cctv_norm     = DataNormalizationLayer.normalize_cctv(segment.get("cctv_count", 0))
    lighting_norm = DataNormalizationLayer.normalize_vibrancy(
        5 if segment.get("safe_zone_flag", False) else 0
    )

    # FAMILIARITY (10 %)
    fam_norm = 1.0 if familiarity_score > _FAM_BASE else 0.5

    # ROAD TYPE (10 %)
    raw_crowd_norm     = DataNormalizationLayer.normalize_crowd(segment.get("crowd_density", 0))
    road_risk          = 1.0 - raw_crowd_norm
    effective_road_risk = min(road_risk * time_mult, 1.0)
    road_type_norm     = 1.0 - effective_road_risk

    impacts = {
        "crime":       round(WEIGHTS["crime"]       * crime_safety_norm * 100.0, 1),
        "cctv":        round(WEIGHTS["cctv"]        * cctv_norm         * 100.0, 1),
        "lighting":    round(WEIGHTS["lighting"]    * lighting_norm     * 100.0, 1),
        "familiarity": round(WEIGHTS["familiarity"] * fam_norm          * 100.0, 1),
        "road_type":   round(WEIGHTS["road_type"]   * road_type_norm    * 100.0, 1),
    }
    total_score  = sum(impacts.values())
    final_score  = float(max(0.0, min(100.0, round(total_score, 1))))
    impacts["time"] = -round((time_mult - 1.0) * (base_density + road_risk) * 10.0, 1)

    return final_score, impacts


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def get_safety_color(score: float) -> str:
    """Map a safety score to a colour band string."""
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange"
    return "red"


def get_unsafe_reasons(segment: dict, safety: float) -> list[str]:
    """Return a list of human-readable reasons why a segment is risky."""
    reasons: list[str] = []
    if segment.get("cctv_count", 0) == 0:
        reasons.append("No CCTV surveillance.")
    if not segment.get("safe_zone_flag", False):
        reasons.append("Few shops or safe zones nearby.")
    return reasons
