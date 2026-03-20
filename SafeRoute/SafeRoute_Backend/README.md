# SafeRoute Backend

FastAPI backend server for the SafeRoute women safety navigation platform, providing AI-driven crime analysis and real-time routing optimization.

## Features

- Safety-optimized route calculation
- Crime density heatmap generation
- DBSCAN danger-zone detection
- Real-time SOS alert broadcasting
- User familiarity tracking

## Tech Stack

- Python 3.9+
- FastAPI
- NetworkX
- NumPy
- scikit-learn
- SQLite
- WebSocket

## Folder Structure

```text
SafeRoute_Backend/
├── main.py → FastAPI server entry point and scheduler setup
├── requirements.txt → Python dependencies list
├── extract_gachibowli_junctions.py → Extracts OSM junctions
├── generate_graph.py → Builds road network from OSM data
├── safe_routes.db → Main SQLite database
├── api/
│   ├── __init__.py → Package initialization
│   └── routes/
│       ├── __init__.py → Package initialization
│       ├── ai_safety.py → Safety scoring endpoints
│       └── crime.py → Crime recording and heatmap endpoints
├── cache/
│   └── f304766c064e321eb0233ea6ed34b452a74bd68e.json → Cached API responses
├── core/
│   ├── config.py → Environment and core configuration
│   ├── safety_config.py → Safety weighting parameters
│   └── security.py → Authentication and API keys
├── data/
│   ├── crime_reports.db → Crime incidents storage
│   ├── gachibowli_complete.json → Full road network JSON
│   ├── gachibowli_edges.json → Road segments with metadata
│   ├── safe_routes.db → Route history storage
│   ├── sos_alerts.db → SOS event storage
│   └── synthetic_safety_data.json → Mock crime data
├── docs/
│   └── gachibowli_safety_map.html → Visualization map
├── services/
│   ├── __init__.py → Package initialization
│   ├── background_jobs.py → APScheduler task definitions
│   ├── crime_heatmap_service.py → Density heatmap generation
│   ├── danger_zone_detector.py → DBSCAN clustering for high-crime areas
│   ├── familiarity_module.py → User travel history tracking
│   ├── incident_severity.py → Crime severity classification
│   ├── rate_limiter.py → API request throttling logic
│   ├── road_graph_generator.py → NetworkX graph compilation
│   ├── route_graph_loader.py → Cached graph memory loading
│   ├── route_safety.py → Core route calculation service
│   ├── safety_engine.py → Score calculation aggregator
│   ├── safety_score_engine.py → Multi-factor safety analysis
│   ├── sos_service.py → Emergency alert handling
│   └── websocket.py → Live broadcasting connections
└── tests/
    ├── test_endpoints.py → Endpoint integration testing
    ├── test_main.py → Application setup testing
    ├── test_osm.py → OSM parsing validation
    ├── test_privacy_compliance.py → Data compliance verification
    └── test_ws.py → Real-time broadcast testing
```

## Setup Instructions

- Ensure Python 3.9+ is installed
- Create and activate a virtual environment
- Install required dependencies from requirements.txt

## Run Commands

- `python -m venv venv`
- `source venv/bin/activate`
- `pip install -r requirements.txt`
- `python main.py`

## Key Functionalities

- Calculates optimal routes balancing safety and time
- Background cron jobs calculate density heatmaps every 5 minutes
- WebSockets broadcast live SOS alerts instantly to clients

## Notes

- Server runs locally on port 8000
- API documentation available at `/docs`
