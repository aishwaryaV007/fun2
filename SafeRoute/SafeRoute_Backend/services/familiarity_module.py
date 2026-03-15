"""
Familiarity Score Module — Safe Route Navigation System
=======================================================
Tracks per-user road-segment travel history and converts visit counts
into normalised familiarity scores used by the route-safety AI.

This module exposes an APIRouter (mounted by main.py) and the
FamiliarityScoreCalculator class for direct import.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, Index, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import DATABASE_URL

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Privacy Audit: Ensure local-only storage
if "sqlite" not in DATABASE_URL:
    logger.warning("PRIVACY WARNING: Non-local database detected. Location data may be transmitted externally.")
else:
    logger.info("Privacy Guard: Local SQLite database confirmed for travel history.")


# ---------------------------------------------------------------------------
# ORM base & models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class UserTravelHistory(Base):
    """One row per (user, segment) pair."""

    __tablename__ = "user_travel_history"
    __table_args__ = (
        Index("idx_user_segment", "user_id", "segment_id", unique=True),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String(255), nullable=False, index=True)
    segment_id   = Column(String(100), nullable=False, index=True)
    visit_count  = Column(Integer, default=1, nullable=False)
    last_visited = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UserProfile(Base):
    """Lightweight user metadata."""

    __tablename__ = "user_profiles"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    user_id        = Column(String(255), unique=True, nullable=False, index=True)
    name           = Column(String(255), nullable=True)
    total_journeys = Column(Integer, default=0, nullable=False)
    created_at     = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_active = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


Base.metadata.create_all(bind=engine)


def _ensure_safe_routes_indexes() -> None:
    """Create idempotent SQLite indexes for frequent familiarity queries."""
    if "sqlite" not in DATABASE_URL:
        return

    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_user_travel_history_last_visited "
            "ON user_travel_history (last_visited)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_user_profiles_last_active "
            "ON user_profiles (last_active)"
        )


_ensure_safe_routes_indexes()


# ---------------------------------------------------------------------------
# DB session dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a scoped session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class RouteCheckRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    segment_ids: List[str] = Field(..., min_length=1, max_length=1000)

    @field_validator("segment_ids")
    @classmethod
    def strip_and_deduplicate(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("segment_ids must contain at least one non-empty value")
        seen: set[str] = set()
        return [x for x in cleaned if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]


class SegmentFamiliarityResponse(BaseModel):
    segment_id:        str
    familiarity_score: float = Field(..., ge=0.0, le=1.0)
    visit_count:       int   = Field(..., ge=0)
    last_visited:      Optional[datetime] = None


class RouteFamiliarityResponse(BaseModel):
    user_id:             str
    total_segments:      int
    familiar_segments:   int
    average_familiarity: float = Field(..., ge=0.0, le=1.0)
    segments:            List[SegmentFamiliarityResponse]


class JourneyCompletionRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    segment_ids: List[str] = Field(..., min_length=1, max_length=1000)

    @field_validator("segment_ids")
    @classmethod
    def strip_segments(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("segment_ids must not be empty after stripping")
        return cleaned


class JourneyCompletionResponse(BaseModel):
    status:                        str
    user_id:                       str
    segments_updated:              int
    new_segments:                  int
    existing_segments_incremented: int
    message:                       str


# ---------------------------------------------------------------------------
# Core business logic
# ---------------------------------------------------------------------------
class FamiliarityScoreCalculator:
    """
    Converts raw visit counts into a [0, 1] familiarity score.

     visits │ score │ rationale
    ────────┼───────┼────────────────────────
       0    │ 0.20  │ unknown territory
       1    │ 0.60  │ memory exists
       2    │ 0.70  │ growing comfort
       3    │ 0.80  │
       4    │ 0.90  │
      5+    │ 1.00  │ daily-commute confidence
    """

    BASE_SCORE: float = 0.20
    FIRST_VISIT: float = 0.60
    INTERPOLATION_STEP: float = 0.10
    MAX_SCORE: float = 1.00
    FAMILIAR_AT: int = 5
    SALT: str = os.getenv("PRIVACY_SALT", "default-safety-salt-change-in-prod")

    @classmethod
    def hash_user_id(cls, user_id: str) -> str:
        """SHA-256 hash with salt for non-reversible identity anonymization."""
        return hashlib.sha256(f"{user_id}{cls.SALT}".encode()).hexdigest()

    @classmethod
    def score(cls, visit_count: int) -> float:
        if visit_count <= 0:
            return cls.BASE_SCORE
        if visit_count == 1:
            return cls.FIRST_VISIT
        if visit_count >= cls.FAMILIAR_AT:
            return cls.MAX_SCORE
        return min(cls.FIRST_VISIT + (visit_count - 1) * cls.INTERPOLATION_STEP, 0.95)

    @staticmethod
    def _fetch_history(
        user_id: str, segment_ids: List[str], db: Session
    ) -> dict[str, UserTravelHistory]:
        rows = (
            db.query(UserTravelHistory)
            .filter(
                UserTravelHistory.user_id == user_id,
                UserTravelHistory.segment_id.in_(segment_ids),
            )
            .all()
        )
        return {r.segment_id: r for r in rows}

    @classmethod
    def calculate_route_familiarity(
        cls, user_id: str, segment_ids: List[str], db: Session,
    ) -> RouteFamiliarityResponse:
        hashed_id = cls.hash_user_id(user_id)
        history = cls._fetch_history(hashed_id, segment_ids, db)
        segment_responses: List[SegmentFamiliarityResponse] = []
        total_score = 0.0
        familiar_count = 0

        for seg_id in segment_ids:
            record = history.get(seg_id)
            visits = record.visit_count if record else 0
            last_visited = record.last_visited if record else None
            familiar_count += 1 if record else 0

            fam = cls.score(visits)
            total_score += fam
            segment_responses.append(
                SegmentFamiliarityResponse(
                    segment_id=seg_id,
                    familiarity_score=round(fam, 2),
                    visit_count=visits,
                    last_visited=last_visited,
                )
            )

        avg = round(total_score / len(segment_ids), 2) if segment_ids else 0.0
        return RouteFamiliarityResponse(
            user_id=user_id,
            total_segments=len(segment_ids),
            familiar_segments=familiar_count,
            average_familiarity=avg,
            segments=segment_responses,
        )

    @classmethod
    def update_travel_history(
        cls, user_id: str, segment_ids: List[str], db: Session,
    ) -> dict:
        hashed_id = cls.hash_user_id(user_id)
        now = datetime.now(timezone.utc)
        unique_ids = list(dict.fromkeys(segment_ids))
        existing = cls._fetch_history(hashed_id, unique_ids, db)
        existing_ids = set(existing.keys())
        new_ids = [s for s in unique_ids if s not in existing_ids]

        for record in existing.values():
            record.visit_count += 1
            record.last_visited = now

        if new_ids:
            db.add_all([
                UserTravelHistory(
                    user_id=hashed_id, segment_id=seg_id,
                    visit_count=1, last_visited=now, created_at=now,
                )
                for seg_id in new_ids
            ])

        db.commit()
        return {
            "new_count": len(new_ids),
            "updated_count": len(existing),
            "total_processed": len(unique_ids),
        }

    @classmethod
    def cleanup_expired_history(cls, db: Session, days: int = 30) -> int:
        """Privacy cleanup: Erase travel history older than X days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = (
            db.query(UserTravelHistory)
            .filter(UserTravelHistory.last_visited < cutoff)
            .delete()
        )
        db.commit()
        if deleted > 0:
            logger.info("Privacy cleanup: Erased %d expired travel records.", deleted)
        return deleted


# ---------------------------------------------------------------------------
# API Router (mounted by main.py)
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api", tags=["Familiarity"])


@router.post(
    "/routes/check-familiarity",
    response_model=RouteFamiliarityResponse,
    summary="Get familiarity scores for a proposed route",
)
async def check_route_familiarity(
    request: RouteCheckRequest, db: Session = Depends(get_db),
):
    try:
        return FamiliarityScoreCalculator.calculate_route_familiarity(
            user_id=request.user_id, segment_ids=request.segment_ids, db=db,
        )
    except Exception as exc:
        logger.exception("check-familiarity failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Familiarity calculation error: {exc}",
        ) from exc


@router.post(
    "/routes/complete-journey",
    response_model=JourneyCompletionResponse,
    summary="Record a completed journey",
)
async def complete_journey(
    request: JourneyCompletionRequest, db: Session = Depends(get_db),
):
    try:
        stats = FamiliarityScoreCalculator.update_travel_history(
            user_id=request.user_id, segment_ids=request.segment_ids, db=db,
        )

        profile = db.query(UserProfile).filter_by(user_id=FamiliarityScoreCalculator.hash_user_id(request.user_id)).first()
        now = datetime.now(timezone.utc)
        if profile:
            profile.total_journeys += 1
            profile.last_active = now
        else:
            db.add(UserProfile(user_id=FamiliarityScoreCalculator.hash_user_id(request.user_id), total_journeys=1, last_active=now))
        db.commit()

        return JourneyCompletionResponse(
            status="success",
            user_id=request.user_id,
            segments_updated=stats["total_processed"],
            new_segments=stats["new_count"],
            existing_segments_incremented=stats["updated_count"],
            message="Travel history updated successfully",
        )
    except Exception as exc:
        db.rollback()
        logger.exception("complete-journey failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Journey update error: {exc}",
        ) from exc


@router.get("/users/{user_id}/stats", summary="User travel statistics")
async def get_user_stats(user_id: str, db: Session = Depends(get_db)):
    history = db.query(UserTravelHistory).filter_by(user_id=user_id).all()
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()

    if not history and not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    total_visits = sum(r.visit_count for r in history)
    total_segments = len(history)
    avg_visits = round(total_visits / total_segments, 2) if total_segments else 0.0
    most_visited = sorted(history, key=lambda r: r.visit_count, reverse=True)[:5]

    return {
        "user_id": user_id,
        "total_segments_visited": total_segments,
        "total_visits": total_visits,
        "total_journeys": profile.total_journeys if profile else 0,
        "avg_visits_per_segment": avg_visits,
        "most_visited_segments": [
            {
                "segment_id": r.segment_id,
                "visit_count": r.visit_count,
                "last_visited": r.last_visited.isoformat(),
            }
            for r in most_visited
        ],
    }


@router.delete("/users/{user_id}/history", summary="Erase travel history (GDPR)")
async def clear_user_history(user_id: str, db: Session = Depends(get_db)):
    try:
        hashed_id = FamiliarityScoreCalculator.hash_user_id(user_id)
        deleted = db.query(UserTravelHistory).filter_by(user_id=hashed_id).delete()
        db.query(UserProfile).filter_by(user_id=hashed_id).delete()
        db.commit()
        return {
            "status": "success",
            "user_id": user_id,
            "records_deleted": deleted,
            "message": "All travel history cleared",
        }
    except Exception as exc:
        db.rollback()
        logger.exception("clear-history failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"History deletion error: {exc}",
        ) from exc
