# SafeRoute

Short Description
- Women safety navigation platform
- AI-driven crime analysis
- Real-time routing optimization
- Live emergency alerts

## Features

- Safety-optimized routes (safest, fastest, balanced)
- Crime heatmap mapping
- Danger-zone detection using DBSCAN
- Real-time SOS alerts via WebSocket
- Contact notifications
- User familiarity-based personalization
- Offline SOS queueing
- Admin dashboard for heatmap visualization

## Tech Stack

- Backend: Python, FastAPI, NetworkX, NumPy, scikit-learn
- Admin: React, TypeScript, Vite, Tailwind CSS
- Mobile: React Native (Expo), react-native-maps
- Database: SQLite (dev), PostgreSQL (prod)
- Cache: Redis
- Realtime: WebSocket

## Architecture

- Mobile Application or Admin Dashboard sends route or SOS requests to FastAPI backend
- Backend calculates paths utilizing NetworkX graph algorithms and OpenStreetMap nodes
- Safety engine applies weights based on crime density (50%), lighting (20%), crowds (15%), and CCTV (15%)
- Background cron jobs calculate density heatmaps and DBSCAN danger clusters every 5 minutes
- WebSockets broadcast live SOS alerts to nearby clients and the admin dashboard instantly

## File Structure

```text
SafeRoute/
├── docker-compose.yml → Orchestrates all services for local deployment
├── README.md → Project documentation
├── SafeRoute_Admin/
│   ├── Dockerfile → Container configuration for the admin dashboard
│   ├── eslint.config.js → Linter configuration
│   ├── index.html → HTML entry point
│   ├── package.json → Dependencies and scripts
│   ├── package-lock.json → Dependency lockfile
│   ├── postcss.config.js → PostCSS configuration
│   ├── tailwind.config.js → Tailwind CSS configuration
│   ├── tsconfig.json → TypeScript configuration
│   ├── tsconfig.app.json → TypeScript app configuration
│   ├── tsconfig.node.json → TypeScript node configuration
│   ├── vite.config.ts → Vite builder configuration
│   ├── public/
│   │   └── vite.svg → Favicon
│   └── src/
│       ├── App.css → Global application styles
│       ├── App.tsx → Main React component layout and routing
│       ├── index.css → Root CSS resets and variables
│       ├── main.tsx → React application initialization
│       ├── assets/
│       │   └── react.svg → React logo asset
│       ├── components/
│       │   ├── AnalyticsCards.tsx → KPI metric display cards
│       │   ├── GoogleMapView.tsx → Map visualization component
│       │   ├── Layout.tsx → Wrapper component for sidebar and content
│       │   ├── Sidebar.tsx → Navigation sidebar
│       │   └── TuningPanel.tsx → Settings adjustment interface
│       └── config/
│           └── backend.ts → Backend API URL configuration
├── SafeRoute_Backend/
│   ├── main.py → FastAPI server entry point and scheduler setup
│   ├── requirements.txt → Python dependencies list
│   ├── extract_gachibowli_junctions.py → Extracts OSM junctions
│   ├── generate_graph.py → Builds road network from OSM data
│   ├── safe_routes.db → Main SQLite database
│   ├── api/
│   │   ├── __init__.py → Package initialization
│   │   └── routes/
│   │       ├── __init__.py → Package initialization
│   │       ├── ai_safety.py → Safety scoring endpoints
│   │       └── crime.py → Crime recording and heatmap endpoints
│   ├── cache/
│   │   └── f304766c064e321eb0233ea6ed34b452a74bd68e.json → Cached API responses
│   ├── core/
│   │   ├── config.py → Environment and core configuration
│   │   ├── safety_config.py → Safety weighting parameters
│   │   └── security.py → Authentication and API keys
│   ├── data/
│   │   ├── crime_reports.db → Crime incidents storage
│   │   ├── gachibowli_complete.json → Full road network JSON
│   │   ├── gachibowli_edges.json → Road segments with metadata
│   │   ├── safe_routes.db → Route history storage
│   │   ├── sos_alerts.db → SOS event storage
│   │   └── synthetic_safety_data.json → Mock crime data
│   ├── docs/
│   │   └── gachibowli_safety_map.html → Visualization map
│   ├── services/
│   │   ├── __init__.py → Package initialization
│   │   ├── background_jobs.py → APScheduler task definitions
│   │   ├── crime_heatmap_service.py → Density heatmap generation
│   │   ├── danger_zone_detector.py → DBSCAN clustering for high-crime areas
│   │   ├── familiarity_module.py → User travel history tracking
│   │   ├── incident_severity.py → Crime severity classification
│   │   ├── rate_limiter.py → API request throttling logic
│   │   ├── road_graph_generator.py → NetworkX graph compilation
│   │   ├── route_graph_loader.py → Cached graph memory loading
│   │   ├── route_safety.py → Core route calculation service
│   │   ├── safety_engine.py → Score calculation aggregator
│   │   ├── safety_score_engine.py → Multi-factor safety analysis
│   │   ├── sos_service.py → Emergency alert handling
│   │   └── websocket.py → Live broadcasting connections
│   └── tests/
│       ├── test_endpoints.py → Endpoint integration testing
│       ├── test_main.py → Application setup testing
│       ├── test_osm.py → OSM parsing validation
│       ├── test_privacy_compliance.py → Data compliance verification
│       └── test_ws.py → Real-time broadcast testing
└── SafeRoute_Native/
    ├── App.tsx → Mobile application entry point
    ├── app.json → Expo configuration settings
    ├── babel.config.js → Babel transformation settings
    ├── package.json → Dependencies and scripts
    ├── package-lock.json → Dependency lockfile
    ├── package-lock 2.json → Backup dependency lockfile
    ├── tsconfig.json → TypeScript configuration
    └── src/
        ├── components/
        │   ├── BottomControls.tsx → Navigational action bar
        │   ├── MapScreen.tsx → Interactive map interface
        │   ├── MiniSOSButton.tsx → Quick-access emergency trigger
        │   ├── RouteSelector.tsx → Selection between route types
        │   └── SOSButton.tsx → Primary emergency interface
        ├── config/
        │   ├── api.ts → Base API endpoint configuration
        │   └── backend.ts → Specific route path definitions
        ├── hooks/
        │   ├── useRealLocation.ts → GPS coordinate retrieval
        │   └── useShakeDetection.ts → Accelerometer listener
        ├── screens/
        │   ├── EmergencyContactsScreen.tsx → Contact management UI
        │   ├── RouteSearchScreen.tsx → Destination input interface
        │   └── SettingsScreen.tsx → Preferences and configuration
        ├── store/
        │   └── useAppStore.ts → Zustand global state manager
        └── utils/
            ├── clientIdentity.ts → Device UUID generator
            ├── logger.ts → Standardized logging utility
            └── mockData.ts → Testing static payloads
```

## Setup Instructions

- Ensure Python 3.9+ is installed
- Ensure Node.js v18+ is installed
- Ensure Expo Go app is installed for mobile testing

## Run Commands

- Backend
  - `cd SafeRoute_Backend`
  - `python -m venv venv`
  - `source venv/bin/activate`
  - `pip install -r requirements.txt`
  - `python main.py`
- Admin Dashboard
  - `cd SafeRoute_Admin`
  - `npm install`
  - `npm run dev`
- Mobile App
  - `cd SafeRoute_Native`
  - `npm install`
  - `npm start`
- Docker Compose
  - `docker-compose up --build`

## API Overview

- `GET /routes/heatmap` → Returns crime density heatmap array
- `GET /routes/danger-zones` → Returns detected high-crime areas
- `POST /routes/safest` → Calculates safety-optimized path
- `POST /routes/fastest` → Calculates standard shortest path
- `POST /sos` → Triggers emergency broadcast
- `GET /sos/active` → Returns live alerts
- `POST /user/register` → Creates a new account
- `GET /health` → Returns system status variables
- `ws://localhost:8000/sos/stream` → Live alert WebSocket connection

## Future Improvements

- Multi-language support (Hindi, Tamil, Telugu)
- Push notifications for SOS alerts
- User feedback system for routes
- Integration with local police department
- Real-time traffic analysis
- Offline map support for mobile app
