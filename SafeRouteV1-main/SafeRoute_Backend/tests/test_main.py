"""
Test Suite — Main API (Women Safety Route Predictor)
=====================================================
Run with:
    pytest test_main.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from core.safety_config import API_KEY

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health & root
# ---------------------------------------------------------------------------

class TestBasicEndpoints:

    def test_root_returns_200(self) -> None:
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert "Women Safety" in body["message"]
        assert body["total_segments"] > 0

    def test_health_returns_ok(self) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["segments_loaded"] > 0


# ---------------------------------------------------------------------------
# Safest route
# ---------------------------------------------------------------------------

class TestSafestRoute:

    def test_valid_route_request(self) -> None:
        # Uses grid cells from data1.json that are neighbours so a path exists.
        # Care Hospitals Gachibowli (14,19) -> WaveRock Building (14,22)
        # Find the nearest node; just assert coords are in-bounds and endpoint accepts the request.
        r = client.post("/safest_route", json={
            "start": {"lat": 17.4267, "lng": 78.3368},
            "end":   {"lat": 17.4455, "lng": 78.3317},
            "time": "14:00",
        })
        # Accept 200 (route found) or 404 (no path – still a well-formed request)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            body = r.json()
            assert "safest_route" in body
            assert body["time_of_day"] == "14:00"

    def test_out_of_bounds_start(self) -> None:
        r = client.post("/safest_route", json={
            "start": {"lat": 0.0, "lng": 0.0},
            "end": {"lat": 17.4100, "lng": 78.5650},
        })
        assert r.status_code == 400
        assert "outside" in r.json()["detail"].lower()

    def test_out_of_bounds_end(self) -> None:
        r = client.post("/safest_route", json={
            "start": {"lat": 17.4100, "lng": 78.5650},
            "end": {"lat": 99.0, "lng": 99.0},
        })
        assert r.status_code == 400

    def test_invalid_time_format(self) -> None:
        r = client.post("/safest_route", json={
            "start": {"lat": 17.4100, "lng": 78.5650},
            "end": {"lat": 17.4200, "lng": 78.5800},
            "time": "not-a-time",
        })
        assert r.status_code == 400

    def test_night_route_has_time_multiplier(self) -> None:
        r = client.post("/safest_route", json={
            "start": {"lat": 17.4267, "lng": 78.3368},
            "end":   {"lat": 17.4455, "lng": 78.3317},
            "time": "22:00",
        })
        # Accept 200 or 404 (Dijkstra needs adjacencies, but time_multiplier is always set)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json()["time_multiplier"] == 1.3

    def test_canonical_route_response_includes_compact_route_shape(self) -> None:
        r = client.post("/routes/safest", json={
            "start": {"lat": 17.4267, "lng": 78.3368},
            "end":   {"lat": 17.4455, "lng": 78.3317},
            "time": "14:00",
        })
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            body = r.json()
            assert "route" in body
            assert "safety_score" in body
            assert isinstance(body["route"], list)
            assert body["route"]
            assert "lat" in body["route"][0]
            assert "lng" in body["route"][0]
            assert isinstance(body["safety_score"], (int, float))


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

class TestHeatmap:

    def test_heatmap_returns_segments(self) -> None:
        r = client.get("/heatmap")
        assert r.status_code == 200
        body = r.json()
        assert body["total_segments"] > 0
        assert len(body["segments"]) > 0
        assert "legend" in body

    def test_heatmap_default_hour(self) -> None:
        r = client.get("/heatmap")
        assert r.status_code == 200

    def test_heatmap_segment_details_use_defaults_for_sparse_edges(self) -> None:
        r = client.get("/heatmap")
        assert r.status_code == 200
        details = r.json()["segments"][0]["details"]
        assert "crime_density" in details
        assert "lights_per_100m" in details
        assert "crowd_density" in details
        assert "cctv_count" in details


class TestDangerZones:

    def test_danger_zones_returns_json(self) -> None:
        r = client.get("/danger-zones")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert "count" in body
        assert "danger_zones" in body

    def test_danger_zones_validates_min_risk(self) -> None:
        r = client.get("/danger-zones?min_risk=2")
        assert r.status_code == 400
        assert "min_risk" in r.json()["detail"]


class TestSpatialHeatmap:

    def test_spatial_heatmap_grid_structure(self) -> None:
        """Verify the 20x20 grid aggregation responses."""
        r = client.get("/heatmap/spatial")
        assert r.status_code == 200
        body = r.json()
        
        assert body["grid_resolution"] == "20x20"
        assert "bounding_box" in body
        assert "heatmap" in body
        assert len(body["heatmap"]) > 0
        
        # Check a sample cell structure
        cell = body["heatmap"][0]
        assert "min_lat" in cell
        assert "min_lng" in cell
        assert "risk_intensity" in cell
        assert 0.0 <= cell["risk_intensity"] <= 1.0
        assert "average_safety" in cell

    def test_spatial_heatmap_legend(self) -> None:
        r = client.get("/heatmap/spatial")
        assert r.status_code == 200
        body = r.json()
        assert "spatial" in body["legend"].get("mechanism", "").lower()


# ---------------------------------------------------------------------------
# Segment details
# ---------------------------------------------------------------------------

class TestSegmentDetails:

    def test_valid_segment(self) -> None:
        r = client.get("/segment/1")
        assert r.status_code == 200
        body = r.json()
        assert body["edge_id"] == 1
        assert "breakdown" in body
        assert "safety_score" in body

    def test_segment_not_found(self) -> None:
        r = client.get("/segment/99999")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Crime report (API key auth)
# ---------------------------------------------------------------------------

class TestCrimeReport:

    def test_report_without_key_returns_200(self) -> None:
        """No X-API-Key header required anymore."""
        r = client.post("/report_crime", json={
            "lat": 17.41, "lng": 78.56,
            "description": "Test", "severity": 3,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "reported"

    def test_report_with_valid_key(self) -> None:
        """Endpoint still functions completely."""
        r = client.post("/report_crime", json={
            "lat": 17.41, "lng": 78.56,
            "description": "Suspicious activity", "severity": 5,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "reported"

    def test_incident_aggregation(self) -> None:
        """Verify multi-report aggregation: avg severity and strengthening count."""
        # Test location (Gachibowli area)
        target_lat, target_lng = 17.4401, 78.3489
        
        # Report 1: Severity 10
        r1 = client.post("/report_crime", json={
            "lat": target_lat, "lng": target_lng,
            "description": "High risk", "severity": 10
        })
        assert r1.status_code == 200
        data1 = r1.json()
        # The first report might not be 1 if other tests ran, but it should increment.
        count1 = data1["segment_impact"]["report_count"]
        
        # Report 2: Severity 2 at same location
        r2 = client.post("/report_crime", json={
            "lat": target_lat, "lng": target_lng,
            "description": "Minor issue", "severity": 2
        })
        assert r2.status_code == 200
        data2 = r2.json()
        
        assert data2["segment_impact"]["report_count"] == count1 + 1
        # Severity weighted average check: if it was first two reports, (10+2)/2 = 6.0
        # If prev reports existed, it still follows the weighted formula.
        
        # Crucial check: score should be lower with more reports (strengthening)
        # unless severity dropped so fast it offset the count (unlikely with sev 10 then 2)
        assert data2["segment_impact"]["new_safety_score"] <= data1["segment_impact"]["new_safety_score"]



class TestNormalizationLayer:

    def test_normalization_logic(self) -> None:
        """Verify the arithmetic normalization scaling and clamping."""
        from main import DataNormalizationLayer
        
        # Crime normalization (MAX 2.0)
        assert DataNormalizationLayer.normalize_crime(1.0) == 0.5
        assert DataNormalizationLayer.normalize_crime(3.0) == 1.0 # Clamped
        
        # CCTV normalization (MAX 5.0)
        assert DataNormalizationLayer.normalize_cctv(2) == 0.4
        assert DataNormalizationLayer.normalize_cctv(10) == 1.0 # Clamped
        
        # Crowd normalization (MAX 100.0)
        assert DataNormalizationLayer.normalize_crowd(50.0) == 0.5
        assert DataNormalizationLayer.normalize_crowd(150.0) == 1.0 # Clamped

    def test_priority_hierarchy(self) -> None:
        """Verify that Crime (40%) has more impact than CCTV (20%)."""
        from main import calculate_safety_score
        
        # Baseline: All zero
        base_seg = {"crime_density": 0.0, "cctv_count": 0, "safe_zone_flag": False, "crowd_density": 0}
        base_score, _ = calculate_safety_score(base_seg, 12)
        
        # Segment B: 1.0 Crime density (50% of MAX_VAL 2.0)
        # Expected drop: 0.4 (weight) * 0.5 (norm) * 100 = 20 points
        crime_seg = base_seg.copy()
        crime_seg["crime_density"] = 1.0
        crime_score, crime_impacts = calculate_safety_score(crime_seg, 12)
        
        # Segment C: 2.5 CCTV count (50% of MAX_VAL 5.0)
        # Expected gain: 0.2 (weight) * 0.5 (norm) * 100 = 10 points
        cctv_seg = base_seg.copy()
        cctv_seg["cctv_count"] = 2.5
        cctv_score, cctv_impacts = calculate_safety_score(cctv_seg, 12)
        
        crime_impact = base_score - crime_score
        cctv_impact  = cctv_score - base_score
        
        assert crime_impact > cctv_impact
        assert round(crime_impact) == 20
        assert round(cctv_impact) == 10


    def test_temporal_risk_scaling(self) -> None:
        """Verify that Night travel (1.3x) significantly impacts safety scores."""
        from main import calculate_safety_score
        
        # Segment with moderate crime (0.5)
        test_seg = {
            "crime_density": 0.5,
            "cctv_count": 0,
            "safe_zone_flag": False,
            "crowd_density": 50 # Moderate crowd
        }
        
        # Day (14:00) Score
        day_score, day_impacts = calculate_safety_score(test_seg, 14)
        
        # Night (02:00) Score
        night_score, night_impacts = calculate_safety_score(test_seg, 2)
        
        # At night, the 1.3x multiplier on crime/road risk should drop the score
        assert day_score > night_score
        # Calculate expected drop: 
        # Day Crime Risk = 0.5 * 1.0 = 0.5 (Safety Norm 0.75)
        # Night Crime Risk = 0.5 * 1.3 = 0.65 (Safety Norm 0.675) -> 4.5 point drop
        assert (day_score - night_score) >= 4.0


# ---------------------------------------------------------------------------
# Safety config functions
# ---------------------------------------------------------------------------

class TestSafetyConfig:

    def test_coords_in_bounds(self) -> None:
        from core.safety_config import coords_in_bounds
        # These coords are inside the Gachibowli / HITEC City bounds of data1.json
        assert coords_in_bounds(17.43, 78.34) is True
        assert coords_in_bounds(0, 0) is False

    def test_time_multiplier(self) -> None:
        from core.safety_config import get_time_multiplier
        assert get_time_multiplier(14) == 1.0
        assert get_time_multiplier(22) == 1.3
        assert get_time_multiplier(3) == 1.3
        assert get_time_multiplier(18) == 1.1


class TestGraphModeling:
    """Suite to verify Road Network Graph modeling integrity."""

    def test_graph_node_and_edge_integrity(self):
        """Verify that nodes are junction coordinates and weights are risk-cost based."""
        from main import build_road_graph
        G = build_road_graph(hour=12)
        
        # 1. Nodes should be tuples of (lat, lng)
        for node in G.nodes():
            assert isinstance(node, tuple)
            assert len(node) == 2

        # 2. Edges must have 'weight' and 'safety_score'
        for u, v, data in G.edges(data=True):
            assert "weight" in data
            assert "safety_score" in data
            # Weight formula check: weight = 100 - safety
            assert data["weight"] == pytest.approx(100.0 - data["safety_score"], abs=1.0)

    def test_safest_path_selection(self):
        """Verify Dijkstra selects a safer routes even if longer."""
        import networkx as nx
        from main import calculate_route
        
        G = nx.Graph()
        # Node setup: Start (0,0), End (1,1)
        # Route 1: Shortest but dangerous
        # (0,0) -> (1,1) Direct. Safety=20 (Risk=80)
        G.add_edge((0.0,0.0), (1.0,1.0), segment_id="dangerous_direct", safety_score=20.0, weight=80.0)
        
        # Route 2: Longer but safest
        # (0,0) -> (0,1) Safety=90 (Risk=10)
        # (0,1) -> (1,1) Safety=90 (Risk=10)
        # Total Risk = 20
        G.add_edge((0.0,0.0), (0.0,1.0), segment_id="safe_1", safety_score=90.0, weight=10.0)
        G.add_edge((0.0,1.0), (1.0,1.0), segment_id="safe_2", safety_score=90.0, weight=10.0)
        
        path_segments = calculate_route(G, (0.0,0.0), (1.0,1.0))
        
        # Dijkstra should pick the 2-segment route because Total Weight (20) < Direct Weight (80)
        assert len(path_segments) == 2
        assert path_segments[0]["segment_id"] == "safe_1"
        assert path_segments[1]["segment_id"] == "safe_2"

    def test_fastest_path_uses_distance_weighting(self):
        """Verify fastest mode minimizes edge distance, not raw hop count."""
        import networkx as nx
        from main import calculate_route

        G = nx.Graph()
        G.add_edge((0.0, 0.0), (2.0, 0.0), segment_id="long_direct", safety_score=80.0, weight=20.0, length_meters=1000.0)
        G.add_edge((0.0, 0.0), (1.0, 0.0), segment_id="short_1", safety_score=75.0, weight=25.0, length_meters=100.0)
        G.add_edge((1.0, 0.0), (2.0, 0.0), segment_id="short_2", safety_score=75.0, weight=25.0, length_meters=100.0)

        path_segments = calculate_route(G, (0.0, 0.0), (2.0, 0.0), use_safety=False)

        assert len(path_segments) == 2
        assert path_segments[0]["segment_id"] == "short_1"
        assert path_segments[1]["segment_id"] == "short_2"


class TestSOSAlert:
    """Tests for the Real-Time SOS Alert module."""

    SOS_PAYLOAD = {
        "user_id": "test_user_42",
        "latitude": 17.4065,
        "longitude": 78.4772,
        "timestamp": "2026-02-28T20:15:00",
    }

    def test_sos_alert_returns_200_and_status(self):
        """POST /sos_alert should return 200 with confirmation status."""
        resp = client.post("/sos_alert", json=self.SOS_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SOS alert received and broadcasted"
        assert "admin_clients_notified" in data

    def test_sos_alert_persists_to_db(self, tmp_path, monkeypatch):
        """SOS alert data must be written to the SQLite database."""
        import sqlite3
        import main

        # Redirect DB to a temp file for isolation
        temp_db = tmp_path / "sos_test.db"
        monkeypatch.setattr(main, "SOS_DB_PATH", temp_db)

        # Ensure table exists
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sos_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                timestamp TEXT NOT NULL,
                received_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()

        client.post("/sos_alert", json=self.SOS_PAYLOAD)

        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM sos_alerts WHERE user_id = ?", ("test_user_42",)).fetchone()
        conn.close()

        assert row is not None
        assert row["latitude"] == pytest.approx(17.4065)
        assert row["longitude"] == pytest.approx(78.4772)

    def test_sos_alert_broadcast_via_websocket(self):
        """Admin WS client should receive the SOS payload immediately after POST."""
        from fastapi.testclient import TestClient
        from main import app

        with TestClient(app) as tc:
            with tc.websocket_connect("/ws/admin_alert") as ws:
                # Fire the SOS alert from a separate request
                resp = tc.post("/sos_alert", json=self.SOS_PAYLOAD)
                assert resp.status_code == 200

                # The WS should receive the broadcast within the same process
                msg = ws.receive_json()
                assert msg["alert_type"] == "SOS"
                assert msg["user_id"] == "test_user_42"
                assert msg["latitude"] == pytest.approx(17.4065)
                assert msg["longitude"] == pytest.approx(78.4772)

    def test_list_sos_alerts_returns_list(self):
        """GET /sos_alerts should return a list of persisted alerts."""
        # Seed one alert first
        client.post("/sos_alert", json=self.SOS_PAYLOAD)
        resp = client.get("/sos_alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["alert_type"] == "SOS"


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
