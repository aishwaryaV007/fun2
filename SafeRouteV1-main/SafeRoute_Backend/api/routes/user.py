"""
ai/api/routes/user.py
======================
User-centric endpoints for the unified SafeRoute AI backend.

Exposes:
  GET  /user/familiarity   — familiarity scores for a user's known segments
  POST /user/complete-journey  — alias for /api/routes/complete-journey

All familiarity logic lives in ai/familiarity_module.py, which is imported
directly. No duplicate storage or logic is introduced.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["User"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FamiliarityRequest(BaseModel):
    user_id: str
    segment_ids: List[str]


class JourneyRequest(BaseModel):
    user_id: str
    segment_ids: List[str]


# ---------------------------------------------------------------------------
# GET /user/familiarity
# ---------------------------------------------------------------------------

@router.post("/familiarity", summary="Get familiarity scores for a set of road segments")
async def get_user_familiarity(request: FamiliarityRequest):
    """
    Returns per-segment familiarity scores for the given user.

    The familiarity score reflects how many times this user has safely
    travelled each segment, boosting their safety score on known routes.

    Input:
        user_id     : string (will be SHA-256 hashed before DB lookup)
        segment_ids : list of segment_id strings

    Returns a dict of { segment_id: familiarity_score } pairs.
    """
    try:
        from services.familiarity_module import FamiliarityScoreCalculator, get_db  # noqa: PLC0415
        db = next(get_db())
        fam_resp = FamiliarityScoreCalculator.calculate_route_familiarity(
            user_id=request.user_id,
            segment_ids=request.segment_ids,
            db=db,
        )
        db.close()
        return {
            "user_id":    request.user_id,
            "familiarity": {
                seg.segment_id: seg.familiarity_score
                for seg in fam_resp.segments
            },
            "total_segments": len(fam_resp.segments),
        }
    except Exception as exc:
        logger.exception("Familiarity lookup failed")
        raise HTTPException(status_code=500, detail=f"Familiarity lookup error: {exc}") from exc


# ---------------------------------------------------------------------------
# GET /user/{user_id}/stats
# ---------------------------------------------------------------------------

@router.get("/{user_id}/stats", summary="Retrieve journey statistics for a user")
async def get_user_stats(user_id: str):
    """
    Returns total journey count and last-active timestamp for the user.
    Delegates entirely to the familiarity module's existing stats function.
    """
    try:
        from services.familiarity_module import get_db, FamiliarityScoreCalculator, UserProfile  # noqa: PLC0415
        db = next(get_db())
        hashed = FamiliarityScoreCalculator.hash_user_id(user_id)
        profile = db.query(UserProfile).filter_by(user_id=hashed).first()
        db.close()

        if not profile:
            return {
                "user_id":       user_id,
                "total_journeys": 0,
                "last_active":   None,
                "message":       "No travel history found for this user.",
            }

        return {
            "user_id":       user_id,
            "total_journeys": profile.total_journeys,
            "last_active":   profile.last_active.isoformat() if profile.last_active else None,
        }
    except Exception as exc:
        logger.exception("User stats lookup failed for user %s", user_id)
        raise HTTPException(status_code=500, detail=f"Stats error: {exc}") from exc


# ---------------------------------------------------------------------------
# POST /user/complete-journey
# ---------------------------------------------------------------------------

@router.post("/complete-journey", summary="Record a completed journey (canonical alias)")
async def complete_journey(request: JourneyRequest):
    """
    Canonical alias for POST /api/routes/complete-journey and POST /complete_journey.

    Records segments as travelled by this user, incrementing familiarity
    scores for future personalised routing.
    """
    try:
        from datetime import datetime, timezone  # noqa: PLC0415
        from services.familiarity_module import (  # noqa: PLC0415
            FamiliarityScoreCalculator, JourneyCompletionResponse,
            UserProfile, get_db,
        )
        db = next(get_db())
        stats = FamiliarityScoreCalculator.update_travel_history(
            user_id=request.user_id,
            segment_ids=request.segment_ids,
            db=db,
        )
        hashed = FamiliarityScoreCalculator.hash_user_id(request.user_id)
        now = datetime.now(timezone.utc)
        profile = db.query(UserProfile).filter_by(user_id=hashed).first()
        if profile:
            profile.total_journeys += 1
            profile.last_active = now
        else:
            db.add(UserProfile(user_id=hashed, total_journeys=1, last_active=now))
        db.commit()
        db.close()
        return JourneyCompletionResponse(
            status="success",
            user_id=request.user_id,
            segments_updated=stats["total_processed"],
            new_segments=stats["new_count"],
            existing_segments_incremented=stats["updated_count"],
            message="Travel history updated. Familiarity scores will improve future routing.",
        )
    except Exception as exc:
        logger.exception("complete-journey failed")
        raise HTTPException(status_code=500, detail=f"Journey update error: {exc}") from exc
