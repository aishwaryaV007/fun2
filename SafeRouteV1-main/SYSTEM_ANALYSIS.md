# SafeRoute System Analysis

## Executive Summary

SafeRoute is a comprehensive **AI-powered women safety navigation system** that combines intelligent routing algorithms, real-time crime analytics, emergency response capabilities, and location-based safety scoring. The system consists of three integrated components:

1. **Backend API** - FastAPI server with routing engine, heatmap analysis, and WebSocket broadcasting
2. **Admin Dashboard** - React web interface for monitoring alerts and visualizing safety data
3. **Mobile Application** - React Native app providing real-time navigation and emergency features

---

## Technologies Used

### Mobile App (React Native with Expo)

**Core Framework:**
- React Native 0.81.5
- Expo 54.0.33
- TypeScript 5.9.2
- React 19.1.0

**State Management:**
- Zustand 4.4.1 (lightweight state store)
- AsyncStorage 2.2.0 (persistent local storage)

**Maps & Location:**
- react-native-maps 1.20.1 (Google Maps integration)
- expo-location 19.0.8 (GPS and location services)
- react-native-shake 6.8.3 (shake detection for SOS)

**Networking:**
- axios 1.13.6 (HTTP client)
- WebSocket support (native)
- Network Info Community 11.4.1 (connectivity detection)

**UI Components:**
- Native React Native components
- Custom styling with StyleSheet

---

### Backend (Python with FastAPI)

**Core Framework:**
- FastAPI 0.115.6 (async web framework)
- Uvicorn 0.32.1 (ASGI server)
- Pydantic 2.9.2 (data validation)

**Routing & Graph Processing:**
- NetworkX 3.2.1 (graph algorithms and routing)
- Dijkstra algorithm implementation (shortest path)
- Road graph loading from OSM data

**Numerical Computing & Algorithms:**
- NumPy 1.26.3 (array operations)
- SciPy 1.16.3 (spatial KD-tree, Gaussian filtering)
- scikit-learn 1.8.0 (DBSCAN clustering for danger zones)

**Geospatial Processing:**
- osmnx 2.1.0 (OpenStreetMap data fetching)
- geopandas 1.1.3 (geospatial dataframes)
- Shapely 2.1.2 (geometric operations)
- geopy 2.4.1 (geocoding)
- pyproj 3.7.2 (coordinate transformations)
- pyogrio 0.12.1 (OGR bindings)

**Database:**
- SQLAlchemy 2.0.25 (ORM)
- SQLite3 (embedded relational DB)
- Three databases: safe_routes.db, sos_alerts.db, crime_reports.db

**Real-time Communication:**
- websockets 16.0 (WebSocket support)
- zeroconf 0.148.0 (mDNS service discovery)

**Scheduling & Tasks:**
- APScheduler 3.11.2 (background job scheduling)
- 5-minute interval for heatmap/danger zone updates

**Data Processing:**
- pandas 3.0.1 (data manipulation)
- requests 2.32.5 (HTTP library)
- httpx 0.26.0 (async HTTP client)

**Development & Testing:**
- pytest 8.0+ (testing framework)
- python-dotenv 1.0.0 (.env file support)
- cachetools 7.0.5 (TTL caching)

---

### Admin Dashboard (React with TypeScript)

**Core Framework:**
- React 19.2.0
- TypeScript 5.9.3
- Vite 7.3.1 (build tool)

**UI & Styling:**
- Tailwind CSS 3.4.19 (utility-first CSS)
- Lucide React 0.575.0 (icon library)
- clsx 2.1.1 (conditional CSS classes)
- tailwind-merge 3.5.0 (Tailwind merging)

**Maps Visualization:**
- @react-google-maps/api 2.20.8 (Google Maps)
- leaflet 1.9.4 (alternative mapping)
- react-leaflet 5.0.0 (Leaflet React wrapper)

**Charts & Analytics:**
- recharts 3.7.0 (charting library)

**Networking:**
- axios 1.13.6 (HTTP client)
- WebSocket support (native browser)

**Build Tools:**
- autoprefixer 10.4.27 (CSS prefixing)
- postcss 8.5.6 (CSS processing)
- ESLint + TypeScript ESLint (code quality)

---

### Database

**SQLite3 Databases:**
1. **safe_routes.db** - User profiles and travel history
   - user_profiles table (user metadata)
   - user_travel_history table (segment visit counts)

2. **sos_alerts.db** - Emergency alerts
   - sos_alerts table (incident records)

3. **crime_reports.db** - Crime incident data
   - crime incidents table (auto-populated)

---

### Maps & Location Services

**Primary Mapping:**
- Google Maps API (Admin Dashboard, Mobile App)
- Leaflet (Admin Dashboard alternative)
- OpenStreetMap (data source)

**Location Services:**
- GPS via expo-location (mobile)
- Geolocation API (web)
- Haversine distance calculations

**Data Sources:**
- gachibowli_complete.json (OSM network structure)
- gachibowli_junctions.json (11,901 road junctions)
- gachibowli_edges.json (28,697 road segments)

---

### Algorithms & AI Logic

**Routing Algorithm:**
- **Dijkstra's Algorithm** - find shortest/safest path between two points
- **K-Shortest Paths** - alternative route generation
- **KD-Tree** (spatial indexing via scipy) - fast nearest-junction lookups

**Safety Scoring:**
- **Multi-factor Weighted Scoring:**
  - Crime Density: 50% weight
  - Lighting Conditions: 20% weight
  - Crowd Density: 15% weight
  - CCTV Coverage: 15% weight

**Heatmap Generation:**
- **Grid-based Crime Density Analysis:**
  - 300m resolution cells
  - Gaussian blur smoothing (sigma=0.006)
  - 30-day decay window for recent incidents
  - Dynamic cell weighting

**Danger Zone Detection:**
- **DBSCAN Clustering:**
  - Haversine distance metric
  - Density-based cluster detection
  - eps=0.015 (≈1.5km), min_samples=5
  - Risk score calculation per zone

**Familiarity Scoring:**
- **User-specific Route Learning:**
  - Per-segment visit count tracking
  - Normalized familiarity scores (0.2 base → 1.0 max)
  - SQLite persistence for privacy
  - Base score boost: familiar routes score +30% higher

**Time-based Safety Multiplier:**
- Dynamic safety adjustments based on time of day
- Peak hours: increased crowd density weight
- Night hours: increased lighting and CCTV weight

---

### Communication Protocols

**API Architecture:**
- **REST API** - synchronous endpoint calls
  - /routes/safest - safe route calculation
  - /routes/fastest - fastest route calculation
  - /routes/score - segment safety scoring
  - /sos/trigger - SOS alert submission
  - /sos/alerts - list recent alerts
  - /user/* - user profile management
  - /crime/report - crime incident submission
  - /health - system health check

**WebSocket Connections:**
- **/sos/stream** - real-time SOS alert broadcast
  - Admin-only connection
  - Immediate alert propagation
  - JSON message format

- **/ws/users** - active user heartbeat
  - User presence tracking
  - Real-time user count
  - Location updates

**Request/Response Format:**
- JSON (application/json)
- CORS enabled for cross-origin requests
- Request validation via Pydantic
- Rate limiting per endpoint

**Security:**
- Optional API key authentication
- Admin key requirement for sensitive endpoints
- WebSocket authentication
- HTTPS/WSS ready for production

---

### Development Tools

**Backend Development:**
- Python 3.14.3+
- pip (package manager)
- pytest (testing framework)
- pytest-cov (coverage reporting)
- black (code formatter)
- mypy (type checking)

**Frontend Development:**
- Node.js 18+ (npm)
- npm (package manager)
- TypeScript compiler
- Vite (dev server, bundler)
- ESLint (linting)
- Prettier (code formatter)

**Version Control:**
- Git
- GitHub repository structure

**Environment Configuration:**
- .env files (environment variables)
- Separate configs for development/production
- API keys and secrets management

---

## How the System Works

### Mobile App Behavior

1. **Map & Navigation**
   - MapScreen mounts with Expo location permission request
   - Shows user's real GPS location (or fallback to Gachibowli coordinates)
   - Displays route polyline from backend or mock data
   - Renders heatmap overlay showing crime density

2. **Route Request**
   - User enters destination coordinates
   - RouteSelector calls POST /routes/safest or /routes/fastest
   - Backend returns polyline, distance, ETA, safety score
   - Route stored in Zustand and displayed on map

3. **SOS Alert**
   - Manual: User taps SOS button → 3-second countdown → send alert
   - Automatic: Device shake detected → haptic feedback → send alert
   - Location included from current GPS position
   - Offline queueing if no internet connection

4. **User Presence**
   - Heartbeat WebSocket connection (/ws/users)
   - Periodic pings to backend for active user tracking
   - Location updates sent to admin dashboard

### Backend Processing

The FastAPI backend processes requests through:

1. **Route Calculation**
   - Load road graph (11,901 junctions, 28,697 edges)
   - Find nearest junctions to start/end locations (KD-tree)
   - Calculate safety weights per segment:
     - Crime density (50%) from heatmap
     - Lighting (20%) from infrastructure data
     - Crowd density (15%) from estimates
     - CCTV coverage (15%) from availability
   - Run Dijkstra's algorithm for safest/fastest path
   - Return polyline with safety score

2. **Safety Scoring**
   - Heatmap integration: Dynamic crime density weighting
   - Danger zone penalties: Proximity-based risk reduction
   - Familiarity boost: +30% for known routes
   - Time-based multipliers: Peak vs off-peak adjustments

3. **SOS Processing**
   - Validate location within bounds
   - Rate limiting: Max 1 alert per 5 seconds
   - Deduplication: 110m radius check
   - Persist to sos_alerts.db
   - Broadcast to all admin WebSocket connections
   - Feed incident to crime heatmap pipeline

4. **Background Updates (5-minute interval)**
   - Regenerate crime heatmap from sos_alerts.db and crime_reports.db
   - Detect danger zones using DBSCAN clustering
   - Recompute route safety weights
   - Update caches (TTL = 5 minutes)

### Database Usage

**SQLite Databases (Local Only):**
- **safe_routes.db**: User profiles and travel history
  - Enables familiarity scoring
  - Stored locally on device/server, never transmitted
- **sos_alerts.db**: Emergency alert records
  - Persists SOS incidents for history/analysis
  - Feeds into crime heatmap generation
- **crime_reports.db**: Crime incident data
  - Stores incidents from all sources
  - Auto-created and populated by background jobs

### Routing Algorithm (Dijkstra)

1. Build weighted graph from road segments
2. Assign edge weights inversely proportional to safety scores
3. Find shortest path from start to end node
4. Return polyline with segment-by-segment safety breakdown
5. Calculate total distance and average safety score
6. Provide alternative routes (k-shortest paths)

### SOS Alert Flow

```
User Trigger (Manual/Shake)
    ↓
Get Current Location
    ↓
Check Network Connectivity
    ├→ Online: Send immediately
    └→ Offline: Queue in AsyncStorage
    ↓
POST /sos/trigger (with retry)
    ↓
Backend Rate Limit & Deduplicate
    ↓
Persist to Database
    ↓
WebSocket Broadcast to Admins
    ↓
Admin Dashboard (Real-time Alert)
    ↓
Admin Clicks "Resolve"
    ↓
POST /sos/{id}/resolve
    ↓
Update Database Status
```

### Admin Dashboard Updates

**Real-time Channels:**
1. WebSocket /sos/stream: Real-time SOS alerts
   - Sub-100ms latency
   - No polling required
   - Persistent connection with reconnection handling

2. HTTP Polling (60-second): Heatmap & statistics
   - GET /routes/score for updated safety data
   - GET /users/count for active user metrics
   - GET /sos/alerts for alert history

**Visualization:**
- GoogleMapView: Crime heatmap overlay with color gradient
- Danger zone circles showing high-risk areas
- Red markers for active SOS alerts
- Green/blue polylines for optimal routes
- Analytics cards with incident counts and metrics

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│                                                                 │
│  Mobile App (React Native)      Admin Dashboard (React/Vite)   │
│  - MapScreen                    - GoogleMapView                │
│  - SOSButton                    - AnalyticsCards               │
│  - RouteSelector                - TuningPanel                  │
│  - BottomControls               - Sidebar                      │
│                                                                 │
│  State: Zustand                 State: React useState          │
│  Storage: AsyncStorage          WebSocket: Native Browser      │
└─────────────────────────────────────────────────────────────────┘
              ↓ REST/WebSocket                ↓ REST/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                          │
│                                                                 │
│  POST /routes/safest       GET /routes/score   POST /sos/trigger
│  POST /routes/fastest      WS /sos/stream      POST /sos/{id}/resolve
│  POST /user/register       WS /ws/users        GET /health       │
│  POST /crime/report        GET /sos/alerts                       │
│                                                                 │
│  Rate Limiting │ CORS │ Auth │ Validation     HTTP/WebSocket   │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  BUSINESS LOGIC LAYER                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Route Service                                           │  │
│  │  - Load junctions (11,901) & edges (28,697)             │  │
│  │  - Build NetworkX graph with safety weights             │  │
│  │  - Dijkstra shortest/safest path                        │  │
│  │  - KD-tree nearest-junction lookup                      │  │
│  │  - K-shortest alternative routes                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Safety Score Engine                                    │  │
│  │  - Crime density (50%) × heatmap weight                 │  │
│  │  - Lighting (20%), Crowd (15%), CCTV (15%)              │  │
│  │  - Danger zone proximity penalties                      │  │
│  │  - Familiarity boost (+30%)                             │  │
│  │  - Time-based multipliers                               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Crime Heatmap Service                                  │  │
│  │  - 300m grid resolution                                 │  │
│  │  - Gaussian blur smoothing                              │  │
│  │  - 30-day incident decay                                │  │
│  │  - Dynamic cell weighting (0.0-1.0)                     │  │
│  │  - 5-minute cache TTL                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Danger Zone Detector (DBSCAN)                          │  │
│  │  - Cluster high-density crime cells                     │  │
│  │  - Haversine distance metric                            │  │
│  │  - eps=1.5km, min_samples=5                             │  │
│  │  - Risk score & radius per zone                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SOS Alert Service                                      │  │
│  │  - Rate limiting (5-sec cooldown)                       │  │
│  │  - Duplicate detection (110m radius)                    │  │
│  │  - Persist to sos_alerts.db                             │  │
│  │  - WebSocket broadcast to admins                        │  │
│  │  - Feed to crime heatmap                                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Familiarity Score Calculator                           │  │
│  │  - Per-user segment visit tracking                      │  │
│  │  - SQLAlchemy ORM with SQLite                           │  │
│  │  - Local-only (privacy-first)                           │  │
│  │  - 0.2 base → 1.0 max score                             │  │
│  │  - +30% boost for familiar routes                       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  WebSocket Connection Manager                           │  │
│  │  - Singleton: AdminConnectionManager                    │  │
│  │  - Broadcast to all admin clients                       │  │
│  │  - Handle reconnection & cleanup                        │  │
│  │  - JSON message serialization                           │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Background Scheduler (APScheduler)                     │  │
│  │  - 5-minute interval                                    │  │
│  │  - Recompute heatmap                                    │  │
│  │  - Detect danger zones                                  │  │
│  │  - Update route weights                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                   │
│                                                                 │
│  SQLite Databases (Local)     JSON Data Files (Road Network)   │
│  - safe_routes.db            - gachibowli_complete.json        │
│  - sos_alerts.db             - gachibowli_junctions.json       │
│  - crime_reports.db          - gachibowli_edges.json           │
│                              - synthetic_safety_data.json       │
│                                                                 │
│  External APIs:                                                │
│  - Google Maps API (visualization)                             │
│  - OpenStreetMap (road data source)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Route Request Flow

```
1. Mobile App → User selects destination
2. RouteSelector.tsx → axios.post("/routes/safest", { start, end, user_id })
3. Backend Routes Handler → Validates coordinates
4. Route Service → Load graph from JSON
5. Route Service → Find nearest junctions (KD-tree)
6. Safety Score Engine → Calculate segment weights
7. Dijkstra Algorithm → Find safest path
8. Response Builder → Format response with polyline + metadata
9. Backend → Return { route, distance, ETA, safety_score, segments }
10. Mobile App → Store in Zustand
11. MapScreen → Render polyline on map
12. User → Selects "Start Navigation"
13. GPS tracking → Real-time position updates on map
```

### SOS Alert Flow

```
1. User → Taps SOS button or device shakes
2. SOSButton.tsx → Get current location (GPS)
3. NetInfo → Check connectivity
   ├→ Online: Send immediately to /sos/trigger
   └→ Offline: Queue in AsyncStorage
4. Backend SOS Handler → Validate location
5. Rate Limiter → Check 5-sec cooldown & 110m radius
6. SOS Service → Persist to sos_alerts.db
7. Admin Broadcaster → admin_manager.broadcast(alert)
8. WebSocket → Send to all connected admin clients
9. Admin Dashboard → Receive alert real-time (< 100ms)
10. Admin → Sees red marker on map + alert card in sidebar
11. Admin → Clicks "Resolve"
12. Backend → Update status = "resolved" in DB
13. Crime Heatmap → Incident feeds into next update
```

### Heatmap Regeneration Flow

```
APScheduler (5-minute interval)
    ↓
Query sos_alerts.db + crime_reports.db (last 30 days)
    ↓
Create 300m grid across Gachibowli bounds
    ↓
Count incidents per cell
    ↓
Apply Gaussian blur smoothing (sigma=0.006)
    ↓
Normalize weights (0.0 → 1.0)
    ↓
DBSCAN clustering on high-weight cells
    ↓
Identify danger zones (center, radius, risk_score)
    ↓
Recompute route segment safety scores
    ↓
Admin Dashboard polling (60-sec interval)
    ↓
GET /routes/score
    ↓
Receive updated heatmap
    ↓
Re-render GoogleMapView with new heatmap layer
```

### User Familiarity Tracking Flow

```
1. User completes journey
2. POST /user/complete-journey { segments: [...] }
3. Backend → For each segment:
   ├─ Query user_travel_history
   ├─ Increment visit_count
   └─ Update last_visited timestamp
4. Database → Persist familiarity data
5. Next route request → Load user's familiar segments
6. Safety Score Engine → Apply +30% boost to familiar segments
7. Dijkstra → Favors familiar routes (lower edge weights)
8. User → Gets safer, more confident routes over time
```

---

## Summary

SafeRoute is a **complete women safety navigation platform** combining:

- **Intelligent Routing**: Dijkstra's algorithm with multi-factor safety scoring
- **Crime Analytics**: Heatmap generation and DBSCAN danger zone detection
- **Emergency Response**: Real-time WebSocket SOS alerts with <100ms latency
- **User Learning**: Local SQLite familiarity tracking for personalized routes
- **Admin Monitoring**: Real-time dashboard with maps and analytics
- **Offline Support**: Automatic SOS queuing for offline scenarios

The system is **modular, scalable, and privacy-respecting** with all user data stored locally and never transmitted externally.
- On startup, the backend:
  - loads routing datasets
  - initializes the SOS database
  - starts the APScheduler background job
  - attempts to publish `saferoute.local` via Zeroconf
- Canonical API groups are mounted for:
  - routing
  - SOS
  - crime reporting
  - user familiarity
  - active-user counting
- The backend validates bounds and payload shapes with Pydantic, applies in-memory rate limiting, and uses TTL caches for route results and route-graph reuse.

## Database Usage

- `crime_reports.db`
  - stores reported crime incidents
  - is read by the heatmap service
  - drives dynamic road-segment safety updates
- `sos_alerts.db`
  - stores every SOS submission
  - is queried by admin alert APIs
  - contributes high-severity signals to the heatmap service while alerts remain active
- `safe_routes.db`
  - stores per-segment helper safety scores in `road_segments`
  - stores familiarity history in `user_travel_history`
  - stores lightweight per-user journey stats in `user_profiles`
- Crime and SOS writes invalidate route, graph, heatmap, and danger-zone caches so later reads use updated safety data.

## Routing Algorithm

- The routing engine loads road-network data from `gachibowli_complete.json` when available, otherwise from separate junction/edge files, and finally from the legacy grid file as a fallback.
- `build_road_graph()` constructs a NetworkX graph where:
  - nodes are junction coordinate tuples
  - edges carry distance, road metadata, and computed safety scores
- Each segment is rescored using the safety engine. Safer segments get lower routing penalties, while risky segments get higher weights.
- Fastest routing uses Dijkstra with `length_meters` as the edge weight.
- Safest routing uses Dijkstra with the derived safety-risk weight.
- If a `user_id` is supplied, the backend looks up per-segment familiarity and folds that into the safety score so repeated routes can feel safer for that user.
- The backend returns both detailed route segments and a compact `route: [{lat, lng}]` list for clients.
- Additional OSM-based endpoints exist under `/routes/osm/*` and use the OSM graph loader for safest, shortest, and balanced route computation.

## SOS Alert Flow

- A mobile SOS event sends:
  - user identifier
  - latitude/longitude
  - timestamp
  - trigger type
  - device metadata
- `sos_service.trigger_and_broadcast()` performs the pipeline:
  1. duplicate/cooldown suppression
  2. SQLite persistence in `sos_alerts.db`
  3. broadcast payload assembly
  4. real-time delivery to connected admin clients
- The backend exposes:
  - `POST /sos/trigger`
  - `GET /sos/alerts`
  - `POST /sos/{id}/resolve`
  - `WS /sos/stream`
- The admin dashboard uses the numeric persisted alert ID to resolve alerts and remove them from the live incident list.

## WebSocket Communication

- `/ws/users`
  - used by mobile devices
  - receives periodic heartbeat messages
  - tracks active-user presence in memory
  - triggers aggregate active-user count broadcasts
- `/sos/stream`
  - used by admin clients
  - broadcasts live SOS payloads
  - also carries active-user count updates through the shared admin connection manager
- The backend connection manager keeps a list of active admin WebSocket connections and fan-outs JSON messages to all connected dashboards.

## Admin Dashboard Updates

- The React + Vite admin app loads initial state from REST:
  - recent alerts from `/sos/alerts`
  - active user count from `/users/count`
- It then opens a WebSocket to `/sos/stream` for live SOS notifications and active-user count updates.
- `GoogleMapView` fetches:
  - `/routes/heatmap`
  - `/danger-zones`
  on an interval and renders those layers on Google Maps.
- Live SOS alerts are rendered as:
  - a map marker
  - a 200 m danger circle
  - a floating critical-alert banner
- The dashboard can resolve an alert through `POST /sos/{id}/resolve`.
- The tuning panel and its chart are local UI visualizations; they do not currently change backend route weights.

# System Architecture

```text
                         +----------------------------------+
                         |        SafeRoute_Native          |
                         |  Expo / React Native mobile app  |
                         |----------------------------------|
                         | GPS, shake detection, SOS queue  |
                         | route planner, heartbeat client  |
                         +----------------+-----------------+
                                          |
                                          | REST + WebSocket
                                          v
+-----------------------------------------------------------------------------------+
|                              SafeRoute_Backend                                    |
|                          FastAPI + Python service layer                           |
|-----------------------------------------------------------------------------------|
| Routers: /routes, /sos, /crime, /user, /users/count                              |
| Services: route_service, safety engines, familiarity, SOS, heatmap, danger zones |
| Runtime: Uvicorn, APScheduler, TTL caches, Zeroconf                              |
+---------------------------+----------------------------+--------------------------+
                            |                            |
                            |                            |
                            v                            v
          +--------------------------------+   +----------------------------------+
          |  Routing Datasets / JSON Graph |   |        SQLite Databases          |
          |--------------------------------|   |----------------------------------|
          | gachibowli_complete.json       |   | crime_reports.db                 |
          | junctions / edges / fallback   |   | sos_alerts.db                    |
          +--------------------------------+   | safe_routes.db                   |
                                               +----------------+-----------------+
                                                                |
                                                                | live SOS / counts
                                                                v
                                  +------------------------------------------------+
                                  |               SafeRoute_Admin                  |
                                  |             React + Vite dashboard             |
                                  |------------------------------------------------|
                                  | Google Maps, heatmap, danger zones, alerts,    |
                                  | incident resolution, analytics, tuning UI      |
                                  +------------------------------------------------+
```

```text
SYSTEM ARCHITECTURE

Mobile App
  ↓
Backend API
  ↓
Routing Engine + Safety Services
  ↓
SQLite Databases + Routing Datasets
  ↓
WebSocket Broadcast
  ↓
Admin Dashboard
```

# Data Flow

## 1. Navigation Request Flow

1. A user opens the mobile app and shares GPS permission.
2. The app resolves the current position through `expo-location`.
3. The user enters source and destination coordinates in the route planner.
4. The mobile app calls `POST /routes/safest` or `POST /routes/fastest`.
5. The backend validates bounds and optional time/user context.
6. The backend loads or reuses the cached NetworkX road graph.
7. If `user_id` is available, familiarity scores are read from `safe_routes.db`.
8. The safety engine scores edges using crime, CCTV, lighting, crowd, time-of-day, and familiarity signals.
9. Dijkstra returns the optimal segment list.
10. The backend responds with compact coordinates plus route statistics.
11. The mobile app stores the route in Zustand and renders the polyline on the map.

## 2. SOS Emergency Flow

1. A mobile user presses the SOS button or triggers it by shaking the device.
2. The app starts a 3-second countdown and gathers the latest device coordinates.
3. If online, the app posts to `POST /sos/trigger`; if offline, it stores the payload in AsyncStorage for later replay.
4. The backend suppresses near-duplicate triggers within the cooldown window.
5. The SOS service persists the alert to `sos_alerts.db`.
6. The SOS service broadcasts the live SOS payload through the shared admin WebSocket manager.
7. Connected admin dashboards receive the event from `/sos/stream`.
8. The dashboard merges the live alert into its alert list, pans the map, and renders a marker plus alert circle.
9. An administrator can resolve the incident through `POST /sos/{id}/resolve`.

## 3. Crime Report to Safety-Layer Flow

1. A crime report arrives at `POST /crime/report`.
2. The backend stores the report in `crime_reports.db`.
3. The nearest logical road segment is identified and its helper safety score is updated in `safe_routes.db`.
4. Route caches, graph caches, heatmap caches, and danger-zone caches are invalidated.
5. The heatmap service later reads recent crime reports plus active SOS alerts.
6. It builds a grid, applies Gaussian smoothing, normalizes weights, and returns heatmap points.
7. The danger-zone detector clusters high-weight heatmap cells into risk zones.
8. The admin dashboard periodically reloads `/routes/heatmap` and `/danger-zones` and updates the map overlays.

## 4. Active User Presence Flow

1. Each mobile app connects to `/ws/users`.
2. The client sends heartbeat pings on an interval.
3. The backend keeps an in-memory registry of currently connected devices.
4. On connect, timeout, or disconnect, the backend recalculates the active-user count.
5. The backend broadcasts aggregate `active_users` messages to admin WebSocket subscribers and also exposes `/users/count` as a REST fallback.
6. The admin dashboard polls `/users/count` and also updates live counts from WebSocket messages.

## 5. End-to-End Operational Flow

```text
User
  ↓
SafeRoute_Native
  ↓
FastAPI REST API / WebSocket
  ↓
Route Graph + Safety Engine + Familiarity Logic
  ↓
SQLite Databases and JSON Routing Data
  ↓
Admin WebSocket Broadcast
  ↓
SafeRoute_Admin Google Maps Dashboard
```
