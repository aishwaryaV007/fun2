"""
Test Suite — Familiarity Score Module
======================================
Run with:
    pytest test_familiarity_module.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.familiarity_module import (
    Base,
    FamiliarityScoreCalculator,
    UserProfile,
    UserTravelHistory,
    get_db,
)
from main import app

# ---------------------------------------------------------------------------
# Test database — isolated in-memory SQLite with StaticPool so all
# connections share the same database instance
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _recreate_tables() -> None:
    Base.metadata.drop_all(bind=_test_engine)
    Base.metadata.create_all(bind=_test_engine)


_recreate_tables()


def _override_get_db() -> Generator[Session, None, None]:
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_tables() -> Generator[None, None, None]:
    _recreate_tables()
    yield


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def user_id() -> str:
    return "test-user-abc123"


@pytest.fixture()
def seeded_history(db: Session, user_id: str) -> list[UserTravelHistory]:
    rows = [
        UserTravelHistory(user_id=user_id, segment_id="seg_0_0", visit_count=5,
                          last_visited=datetime.now(timezone.utc)),
        UserTravelHistory(user_id=user_id, segment_id="seg_0_1", visit_count=2,
                          last_visited=datetime.now(timezone.utc)),
        UserTravelHistory(user_id=user_id, segment_id="seg_0_2", visit_count=1,
                          last_visited=datetime.now(timezone.utc)),
    ]
    db.add_all(rows)
    db.commit()
    return rows


# ---------------------------------------------------------------------------
# Scoring algorithm
# ---------------------------------------------------------------------------
class TestScoringAlgorithm:

    @pytest.mark.parametrize("visits,expected", [
        (0,   0.20),
        (1,   0.60),
        (2,   0.70),
        (3,   0.80),
        (4,   0.90),
        (5,   1.00),
        (10,  1.00),
        (100, 1.00),
    ])
    def test_score_curve(self, visits: int, expected: float) -> None:
        assert FamiliarityScoreCalculator.score(visits) == expected

    def test_score_is_monotonically_non_decreasing(self) -> None:
        scores = [FamiliarityScoreCalculator.score(v) for v in range(15)]
        assert scores == sorted(scores)

    def test_negative_visits_treated_as_zero(self) -> None:
        assert FamiliarityScoreCalculator.score(-1) == 0.20


# ---------------------------------------------------------------------------
# Route familiarity calculation
# ---------------------------------------------------------------------------
class TestCalculateRouteFamiliarity:

    def test_all_unfamiliar(self, db: Session, user_id: str) -> None:
        result = FamiliarityScoreCalculator.calculate_route_familiarity(
            user_id, ["seg_99_99", "seg_99_98"], db
        )
        assert result.familiar_segments == 0
        assert result.average_familiarity == 0.20

    def test_mixed_history(
        self, db: Session, user_id: str, seeded_history: list
    ) -> None:
        seg_ids = ["seg_0_0", "seg_0_1", "seg_0_2", "seg_9_9", "seg_9_8"]
        result = FamiliarityScoreCalculator.calculate_route_familiarity(
            user_id, seg_ids, db
        )
        assert result.total_segments == 5
        assert result.familiar_segments == 3

        scores = {s.segment_id: s for s in result.segments}
        assert scores["seg_0_0"].familiarity_score == 1.00
        assert scores["seg_0_1"].familiarity_score == 0.70
        assert scores["seg_0_2"].familiarity_score == 0.60


# ---------------------------------------------------------------------------
# Travel history updates
# ---------------------------------------------------------------------------
class TestUpdateTravelHistory:

    def test_new_segments_inserted(self, db: Session, user_id: str) -> None:
        stats = FamiliarityScoreCalculator.update_travel_history(
            user_id, ["seg_A", "seg_B", "seg_C"], db
        )
        assert stats == {"new_count": 3, "updated_count": 0, "total_processed": 3}

    def test_existing_segments_incremented(
        self, db: Session, user_id: str, seeded_history: list
    ) -> None:
        stats = FamiliarityScoreCalculator.update_travel_history(
            user_id, ["seg_0_0", "seg_0_1"], db
        )
        assert stats["updated_count"] == 2

        row = db.query(UserTravelHistory).filter_by(
            user_id=user_id, segment_id="seg_0_0"
        ).first()
        assert row.visit_count == 6


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
class TestFamiliarityAPIEndpoints:

    def test_check_familiarity_new_user(self) -> None:
        r = client.post("/api/routes/check-familiarity", json={
            "user_id": "brand-new-user",
            "segment_ids": ["seg_5_5", "seg_6_6"],
        })
        assert r.status_code == 200
        body = r.json()
        assert body["familiar_segments"] == 0

    def test_check_familiarity_empty_list_rejected(self) -> None:
        r = client.post("/api/routes/check-familiarity", json={
            "user_id": "u1",
            "segment_ids": [],
        })
        assert r.status_code == 422

    def test_complete_journey_creates_records(self) -> None:
        uid = "journey-create-user"
        r = client.post("/api/routes/complete-journey", json={
            "user_id": uid,
            "segment_ids": ["seg_10_10", "seg_10_11", "seg_10_12"],
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert body["new_segments"] == 3

    def test_user_stats_not_found(self) -> None:
        r = client.get("/api/users/nobody-here/stats")
        assert r.status_code == 404

    def test_clear_history(self) -> None:
        uid = "delete-me-user"
        client.post("/api/routes/complete-journey", json={
            "user_id": uid, "segment_ids": ["seg_X_1", "seg_X_2"],
        })
        r = client.delete(f"/api/users/{uid}/history")
        assert r.status_code == 200
        assert r.json()["records_deleted"] == 2


# ---------------------------------------------------------------------------
# Integration: full lifecycle
# ---------------------------------------------------------------------------
class TestIntegration:

    def test_full_new_user_lifecycle(self) -> None:
        uid = "integration-lifecycle"
        segs = ["seg_30_1", "seg_30_2", "seg_30_3"]

        r = client.post("/api/routes/check-familiarity",
                        json={"user_id": uid, "segment_ids": segs})
        assert r.json()["familiar_segments"] == 0

        client.post("/api/routes/complete-journey",
                    json={"user_id": uid, "segment_ids": segs})

        r2 = client.post("/api/routes/check-familiarity",
                         json={"user_id": uid, "segment_ids": segs})
        body = r2.json()
        assert body["familiar_segments"] == 3
        assert body["average_familiarity"] == 0.6

    def test_familiarity_reaches_max_after_five_journeys(self) -> None:
        uid = "repeat-traveller"
        segs = ["seg_31_31"]
        for _ in range(5):
            client.post("/api/routes/complete-journey",
                        json={"user_id": uid, "segment_ids": segs})

        r = client.post("/api/routes/check-familiarity",
                        json={"user_id": uid, "segment_ids": segs})
        seg = r.json()["segments"][0]
        assert seg["familiarity_score"] == 1.0
        assert seg["visit_count"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
