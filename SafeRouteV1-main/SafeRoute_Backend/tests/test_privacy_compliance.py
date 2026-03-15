import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.familiarity_module import Base, UserTravelHistory, FamiliarityScoreCalculator
from datetime import datetime, timedelta, timezone

# Setup in-memory SQLite for testing privacy logic
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_user_id_anonymization(db):
    """Verify that raw user IDs are hashed before storage."""
    raw_user_id = "gaurav@example.com"
    segments = ["seg_A", "seg_B"]
    
    # Update history
    FamiliarityScoreCalculator.update_travel_history(raw_user_id, segments, db)
    
    # Query DB directly to check contents
    records = db.query(UserTravelHistory).all()
    assert len(records) == 2
    
    for r in records:
        # The stored user_id should NOT be the raw email
        assert r.user_id != raw_user_id
        # It should be a 64-char hex string (SHA-256)
        assert len(r.user_id) == 64
        # Verify it matches the calculator's hash
        assert r.user_id == FamiliarityScoreCalculator.hash_user_id(raw_user_id)

def test_data_pruning_logic(db):
    """Verify that history older than 30 days is erased."""
    hashed_id = FamiliarityScoreCalculator.hash_user_id("test_user")
    now = datetime.now(timezone.utc)
    
    # 1. Add Fresh record
    db.add(UserTravelHistory(
        user_id=hashed_id,
        segment_id="fresh_seg",
        visit_count=1,
        last_visited=now
    ))
    
    # 2. Add Expired record (31 days ago)
    expired_time = now - timedelta(days=31)
    db.add(UserTravelHistory(
        user_id=hashed_id,
        segment_id="expired_seg",
        visit_count=5,
        last_visited=expired_time
    ))
    db.commit()
    
    assert db.query(UserTravelHistory).count() == 2
    
    # Run cleanup
    deleted_count = FamiliarityScoreCalculator.cleanup_expired_history(db, days=30)
    
    assert deleted_count == 1
    assert db.query(UserTravelHistory).count() == 1
    
    remaining = db.query(UserTravelHistory).first()
    assert remaining.segment_id == "fresh_seg"

def test_familiarity_retrieval_with_hashing(db):
    """Verify that retrieval works correctly with the hashing layer."""
    raw_user_id = "privacy_user_123"
    seg_id = "test_seg_99"
    
    # 1. Seed data as if user travelled
    FamiliarityScoreCalculator.update_travel_history(raw_user_id, [seg_id], db)
    
    # 2. Check familiarity using raw ID
    resp = FamiliarityScoreCalculator.calculate_route_familiarity(raw_user_id, [seg_id], db)
    
    assert resp.user_id == raw_user_id # Response returns the requested ID for frontend context
    assert resp.segments[0].visit_count == 1
    # Score for 1 visit is 0.6
    assert resp.segments[0].familiarity_score == 0.6
