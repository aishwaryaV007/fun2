from fastapi import APIRouter, Query
from typing import List, Dict, Optional

from services.crime_heatmap_service import get_heatmap_service
from services.danger_zone_detector import get_danger_zone_detector

router = APIRouter(prefix="/ai-safety", tags=["AI Safety Analysis"])

@router.get("/heatmap")
async def get_ai_heatmap(
    force_refresh: bool = Query(default=False),
    hour: Optional[int] = Query(default=None)
):
    """
    AI Crime Heatmap - grid-based density from crimes + SOS.
    Returns list of {latitude, longitude, weight} points.
    """
    service = get_heatmap_service()
    if hour is not None:
        # Note: hour param not yet used in heatmap (add time-decay later)
        pass
    return service.get_heatmap(force_refresh=force_refresh)

@router.get("/danger-zones")
async def get_danger_zones(
    force_refresh: bool = Query(default=False),
    min_risk: float = Query(default=0.3, ge=0.0, le=1.0)
):
    """
    DBSCAN danger zone clusters from heatmap.
    Returns list of {center_lat, center_lng, radius_degrees, risk_score, cluster_size}.
    """
    detector = get_danger_zone_detector()
    return detector.detect_danger_zones(force_refresh=force_refresh, min_risk=min_risk)

@router.get("/safety-test")
async def test_safety_integration():
    """
    Test endpoint: verify services load + sample data.
    """
    try:
        heatmap_sample = get_heatmap_service().get_heatmap()[0:3]
        zones_sample = get_danger_zone_detector().detect_danger_zones()[0:2]
        return {
            "status": "ok",
            "heatmap_sample": heatmap_sample,
            "danger_zones_sample": zones_sample,
            "services_ready": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

