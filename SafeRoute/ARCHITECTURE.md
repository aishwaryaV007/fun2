# SafeRoute Architecture

Complete architectural overview of the SafeRoute system, design patterns, scalability strategies, and technology rationale.

---

## 1. System Architecture Overview

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Mobile App  │  │  Admin       │  │  Web         │       │
│  │  (React      │  │  Dashboard   │  │  Interface   │       │
│  │  Native)     │  │  (React)     │  │  (Future)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
              ↓ HTTPS/WebSocket ↓
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         FastAPI Backend (Python 3.11)               │   │
│  │  ┌─────────────┐  ┌──────────────┐ ┌─────────────┐ │   │
│  │  │  API        │  │  WebSocket   │ │  Services   │ │   │
│  │  │  Routes     │  │  Manager     │ │  Layer      │ │   │
│  │  └─────────────┘  └──────────────┘ └─────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │  Route       │ │  Safety      │ │  SOS            │    │
│  │  Calculation │ │  Engine      │ │  Service        │    │
│  │  Engine      │ │              │ │                 │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
              ↓ SQL/Cache Queries ↓
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Database    │  │  Cache       │  │  File        │      │
│  │  (SQLite/    │  │  (Redis)     │  │  Storage     │      │
│  │  PostgreSQL) │  │              │  │  (JSON Data) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### Backend Components

#### 2.1 API Routes Layer (`api/routes/`)

Handles HTTP request routing and validation.

```
api/routes/
├── routes.py         # Route calculation endpoints
├── sos.py            # Emergency alert endpoints
├── crime.py          # Crime data endpoints
├── user.py           # User profile endpoints
├── active_users.py   # Real-time user tracking
└── __init__.py
```

**Responsibilities:**
- Request validation using Pydantic models
- Authentication and authorization checks
- Rate limiting and quota enforcement
- Response serialization and error handling

**Key Patterns:**
- FastAPI dependency injection for authentication
- Pydantic BaseModel for request/response validation
- OpenAPI/Swagger documentation auto-generation

---

#### 2.2 Services Layer (`services/`)

Core business logic and algorithm implementation.

```
services/
├── route_service.py              # Route management
├── route_safety.py               # Safety analysis
├── route_scoring_engine.py        # Route scoring algorithm
├── safety_engine.py              # Area safety assessment
├── familiarity_module.py          # User familiarity tracking
├── incident_severity.py           # Incident classification
├── sos_service.py                # Emergency handling
├── websocket.py                  # WebSocket management
└── __init__.py
```

**Service Responsibilities:**

**RouteService**
- Path finding using Dijkstra/A* algorithms
- Route optimization and ranking
- Distance and time calculations
- Integration with external map APIs

**SafetyEngine**
- Crime density calculation
- Lighting assessment
- Crowd density analysis
- CCTV coverage evaluation
- Composite safety score generation

**FamiliarityModule**
- Track user travel history per edge
- Calculate familiarity scores
- Identify routine routes
- Personalize recommendations

**SOSService**
- Alert creation and broadcasting
- Contact notification (SMS/email)
- Emergency responder coordination
- Historical tracking and reporting

---

#### 2.3 Core Layer (`core/`)

Configuration and security utilities.

```
core/
├── config.py         # Configuration management
├── safety_config.py  # Safety parameters
├── security.py       # Authentication & encryption
└── __init__.py
```

**Key Components:**

```python
# config.py
class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_MAPS_API_KEY: str
    SAFETY_API_KEY: str
    REDIS_URL: Optional[str]
    CORS_ORIGINS: list
    LOG_LEVEL: str
    
    class Config:
        env_file = ".env"

# security.py
def verify_api_key(api_key: str) -> bool:
    """Validate API key against database or environment"""
    pass

def create_jwt_token(user_id: str) -> str:
    """Generate JWT for authenticated users"""
    pass
```

---

#### 2.4 Data Layer (`data/`)

Contains reference data files and static datasets.

```
data/
├── gachibowli_complete.json      # Full map data
├── gachibowli_junctions.json      # Intersection points
├── gachibowli_edges.json          # Street segments
├── synthetic_safety_data.json     # Historical crime data
└── data1.json                     # Additional reference data
```

---

### Frontend Components

#### 2.5 Mobile App (`SafeRoute_Native/src/`)

React Native application for iOS/Android.

```
src/
├── components/
│   ├── MapScreen.tsx             # Main map interface
│   ├── SOSButton.tsx             # Emergency button
│   └── BottomControls.tsx         # Route controls
├── store/
│   └── useAppStore.ts            # Zustand state management
├── utils/
│   └── mockData.ts               # Test data
└── App.tsx                       # Root component
```

**Key Features:**
- Real-time location tracking
- Route visualization on map
- One-tap SOS functionality
- Live emergency responder tracking
- User profile management

---

#### 2.6 Admin Dashboard (`SafeRoute_Admin/src/`)

React web application for system administration.

```
src/
├── components/
│   ├── MapView.tsx               # Crime heatmap
│   ├── AnalyticsCards.tsx         # Metrics dashboard
│   ├── TuningPanel.tsx            # Algorithm parameters
│   ├── Sidebar.tsx                # Navigation
│   └── Layout.tsx                 # Page layout
├── App.tsx                       # Root component
├── App.css                       # Styling
└── main.tsx                      # Entry point
```

**Admin Capabilities:**
- Real-time SOS alert monitoring
- Crime heatmap visualization
- Active user location tracking
- Safety algorithm tuning
- Analytics and reporting
- System health monitoring

---

## 3. Data Flow Diagrams

### 3.1 Route Calculation Flow

```
User Request
    ↓
API Validation (POST /routes/safest)
    ↓
Authenticate & Check Rate Limit
    ↓
Load Map Data (gachibowli_complete.json)
    ↓
Initialize Route Engine
    ↓
Apply Path Finding Algorithm (Dijkstra/A*)
    ↓
Calculate Safety Score for Each Segment
    │ ├─ Crime Density (from synthetic_safety_data.json)
    │ ├─ Lighting Analysis
    │ ├─ Crowd Density Estimation
    │ └─ CCTV Coverage
    ↓
Apply User Familiarity Multiplier
    ↓
Generate Alternative Routes (Safest, Fastest, Balanced)
    ↓
Cache Result (Redis or Memory)
    ↓
Return JSON Response
    ↓
Update User Travel History
```

### 3.2 SOS Alert Flow

```
User Triggers SOS
    ↓
API Validation & Rate Limit Check
    ↓
Create Alert Record (Database)
    ↓
Broadcast to WebSocket Clients
    │ ├─ Admin Dashboard (Real-time update)
    │ ├─ Emergency Responders (Mobile)
    │ └─ System Monitors
    ↓
Notify Emergency Contacts (SMS/Email)
    ↓
Log Incident (Sentry)
    ↓
Assign Responders
    ↓
Send Status Updates via WebSocket
    ↓
Mark Resolved
    ↓
Generate Report
```

### 3.3 Real-Time Updates Flow

```
Mobile App / Admin Dashboard
    ↓ (WebSocket Connection)
Backend WebSocket Handler
    ↓
Message Router
    ├─ Active User Updates
    ├─ SOS Broadcasts
    ├─ Safety Alerts
    └─ System Notifications
    ↓
Broadcast to Connected Clients
    ↓
Update UI in Real-Time
```

---

## 4. Technology Rationale

### Backend Selection: FastAPI

**Why FastAPI?**
- **Performance:** Built on Starlette, one of fastest Python frameworks
- **Async Support:** Native async/await for concurrent request handling
- **Type Hints:** Pydantic integration for validation and documentation
- **Auto Documentation:** Swagger UI and ReDoc auto-generated
- **WebSocket Support:** Built-in WebSocket handling for real-time updates
- **Modern Python:** Leverage Python 3.11+ features

**Alternative Considered:** Django REST Framework
- More mature but heavier
- Synchronous by default
- Slower for high-concurrency scenarios

---

### Frontend Selection: React

**Why React?**
- **Component Reusability:** Build complex UIs from simple components
- **Performance:** Virtual DOM optimization
- **React Native:** Share code between web, iOS, Android
- **Ecosystem:** Extensive library ecosystem
- **Developer Experience:** Hot module reloading, great tooling

---

### Mobile: React Native + Expo

**Why React Native?**
- **Code Sharing:** Single codebase for iOS and Android
- **Development Speed:** Live reloading and hot updates
- **Native Performance:** Direct access to device APIs

**Why Expo?**
- Simplified build and deployment process
- OTA (Over-The-Air) updates without app store
- Rich set of pre-built modules

---

### Database: SQLite → PostgreSQL

**Development (SQLite)**
- Lightweight, serverless
- Perfect for rapid development
- No external dependencies

**Production (PostgreSQL)**
- Multi-client concurrent access
- ACID transactions and reliability
- Advanced features (JSON, Full-text search)
- Replication and backup capabilities
- Performance under load

**Migration Path:**
```sql
-- Export from SQLite
.mode insert routes
.output routes.sql
SELECT * FROM routes;

-- Import to PostgreSQL
psql -d saferoute < routes.sql
```

---

### Caching: Redis

**Use Cases:**
- Route calculation results
- Heatmap grid data (expensive to compute)
- User sessions and tokens
- Real-time location data
- Rate limit counters

**Cache Strategy:**
```
1. Check Redis cache → Return if hit (< 10ms)
2. Calculate if miss → Store in cache
3. Set TTL based on data volatility
4. Invalidate on data changes
```

---

## 5. Scalability Architecture

### 5.1 Horizontal Scaling

```
Load Balancer (Nginx/HAProxy)
        ↓
    ┌───┴───┬────────┬────────┐
    ↓       ↓        ↓        ↓
  API-1   API-2    API-3    API-N
    │       │        │        │
    └───┬───┴───┬────┴───┬────┘
        ↓       ↓        ↓
    Shared Database (PostgreSQL)
    Shared Cache (Redis)
    Shared File Storage (S3/GCS)
```

**Scaling Strategy:**
1. **Stateless API Servers:** Each instance independent
2. **Load Balancer:** Distribute requests (round-robin/least connections)
3. **Shared Infrastructure:** Database, cache, storage
4. **Auto-scaling:** Based on CPU/memory/request metrics

---

### 5.2 Database Scaling

**Read Replicas:**
```
Write Master (PostgreSQL)
    ↓
    ├─ Read Replica 1 (for analytics)
    ├─ Read Replica 2 (for searches)
    └─ Read Replica 3 (for backup)
```

**Connection Pooling:**
```python
# Using PgBouncer
- Reduce connection overhead
- Multiplexing connections across servers
- Improved throughput under load
```

**Caching Strategy:**
```
Routes Endpoint
    ↓
Check Redis Cache
    ├─ Cache HIT (< 10ms) → Return
    └─ Cache MISS → Query DB → Store in Redis
```

---

### 5.3 WebSocket Scaling

**Current Single Server:**
```
Server 1
├─ Route Calculation
├─ WebSocket Manager
└─ SOS Broadcast
```

**Scaled Multi-Server:**
```
Load Balancer (Sticky Sessions)
    ↓
    ├─ Server 1 (1000 connections)
    ├─ Server 2 (1000 connections)
    └─ Server 3 (1000 connections)
    
Message Broker (Redis Pub/Sub)
├─ Broadcast SOS to all servers
├─ Real-time user updates
└─ System notifications
```

**Implementation:**
```python
# Redis Pub/Sub for cross-server messaging
redis = aioredis.from_url("redis://")

# Server 1 publishes SOS
await redis.publish("sos-alerts", sos_data)

# All servers receive and broadcast to WebSocket clients
async def handle_sos_broadcast():
    pubsub = await redis.subscribe("sos-alerts")
    async for message in pubsub.iter():
        await broadcast_to_websockets(message)
```

---

### 5.4 Microservices Migration Path

**Current Monolithic:**
```
Single FastAPI Application
├─ Route Service
├─ Safety Engine
├─ SOS Service
├─ User Service
└─ Admin Dashboard Backend
```

**Future Microservices:**
```
API Gateway (Nginx)
    ↓
    ├─ Route Service (Port 8001)
    ├─ Safety Service (Port 8002)
    ├─ SOS Service (Port 8003)
    ├─ User Service (Port 8004)
    └─ Admin Service (Port 8005)

Message Queue (RabbitMQ/Kafka)
    └─ Async job processing and inter-service communication

Service Registry (Consul/Eureka)
    └─ Dynamic service discovery
```

**Benefits:**
- Independent scaling per service
- Fault isolation (1 service down ≠ entire system down)
- Technology flexibility per service
- Easier deployment and updates

---

## 6. Security Architecture

### 6.1 API Authentication Flow

```
Client Request
    ↓
Include API Key Header (X-API-Key) or JWT Bearer Token
    ↓
API Gateway / Rate Limiter
    ↓
Verify Credentials
    ├─ Invalid → Return 401 Unauthorized
    └─ Valid → Continue
    ↓
Check Rate Limits
    ├─ Exceeded → Return 429 Too Many Requests
    └─ OK → Continue
    ↓
Extract User ID / Role
    ↓
Process Request with Authorization Context
```

### 6.2 WebSocket Security

```
WebSocket Connection
    ↓
Verify API Key in Query Parameter
    ├─ Invalid → Close connection
    └─ Valid → Establish connection
    ↓
Authenticate Each Message (if applicable)
    ↓
Validate Message Schema
    ↓
Rate Limit Per-Connection
    ↓
Log All Access
```

### 6.3 Data Encryption

```
In Transit:
├─ HTTPS/TLS 1.3 for REST API
├─ WSS (WebSocket Secure) for real-time
└─ TLS for database connections

At Rest:
├─ Database encryption (PostgreSQL pgcrypto)
├─ API keys hashed in database
├─ Sensitive user data encrypted
└─ Backups encrypted (AES-256)
```

---

## 7. Deployment Architecture

### 7.1 Development Environment

```
Local Machine
├─ Docker Desktop
├─ docker-compose.yml
│   ├─ Backend Service (FastAPI)
│   ├─ Admin Dashboard (React)
│   └─ SQLite Database
├─ Frontend Dev Server (Vite)
├─ Mobile Emulator (iOS/Android)
└─ Redis (Optional local)
```

### 7.2 Production Environment

```
AWS / GCP / Azure
├─ Container Registry (ECR / GCR / ACR)
│
├─ Load Balancer
│   └─ HTTPS/TLS Termination
│
├─ Auto Scaling Group
│   ├─ API Server 1 (ECS / Cloud Run / Container Instances)
│   ├─ API Server 2
│   ├─ API Server N
│   └─ Health Checks
│
├─ Managed Database
│   ├─ PostgreSQL (RDS / Cloud SQL / Azure Database)
│   ├─ Automated Backups
│   ├─ Read Replicas
│   └─ Failover Setup
│
├─ Cache Layer
│   └─ Managed Redis (ElastiCache / Memorystore / Azure Cache)
│
├─ Storage
│   └─ Object Storage (S3 / GCS / Blob Storage)
│
└─ CDN
    └─ CloudFront / Cloud CDN / Azure CDN
```

### 7.3 Kubernetes Architecture

```
Namespace: saferoute-prod
│
├─ Deployment: api-backend
│   ├─ Replicas: 3-10 (auto-scale)
│   ├─ Container: saferoute:latest
│   ├─ Resources: 512Mi RAM, 250m CPU
│   ├─ Liveness Probe: /health
│   ├─ Readiness Probe: /ready
│   └─ Service: api-backend-svc (LoadBalancer)
│
├─ Deployment: admin-dashboard
│   ├─ Replicas: 2-5
│   ├─ Container: saferoute-admin:latest
│   └─ Service: admin-svc (ClusterIP)
│
├─ StatefulSet: postgres
│   ├─ Replicas: 1 (primary) + 2 (replicas)
│   ├─ PersistentVolume: 100Gi
│   └─ Service: postgres-svc
│
├─ StatefulSet: redis
│   ├─ Replicas: 1
│   ├─ PersistentVolume: 10Gi
│   └─ Service: redis-svc
│
├─ ConfigMap: api-config
│   └─ Environment variables
│
├─ Secret: api-secrets
│   ├─ Database credentials
│   ├─ API keys
│   └─ JWT secret
│
├─ HPA: api-backend
│   ├─ Min: 3 replicas
│   ├─ Max: 10 replicas
│   ├─ Target CPU: 70%
│   └─ Target Memory: 80%
│
└─ Ingress: saferoute-ingress
    ├─ Host: api.saferoute.example.com
    ├─ TLS: Let's Encrypt
    └─ Routes: /routes → api-backend-svc, /admin → admin-svc
```

---

## 8. Monitoring & Observability

### 8.1 Metrics Collection

```
Application
├─ Route calculation time
├─ WebSocket connection count
├─ SOS trigger frequency
├─ API response times (P50, P95, P99)
└─ Error rates by endpoint

Infrastructure
├─ CPU utilization
├─ Memory usage
├─ Disk I/O
├─ Network throughput
└─ Container/Pod metrics

Database
├─ Query latency
├─ Connection pool usage
├─ Replication lag
└─ Backup success
```

### 8.2 Logging Architecture

```
Application Logs
    ↓
JSON Structured Logging
    ├─ Timestamp
    ├─ Log Level (DEBUG, INFO, WARNING, ERROR)
    ├─ Request ID (for tracing)
    ├─ User ID (for debugging)
    └─ Message + Context
    ↓
Log Aggregation (ELK Stack / CloudWatch)
    ├─ Elasticsearch: Store and index logs
    ├─ Logstash: Parse and transform logs
    └─ Kibana: Visualize and search
```

### 8.3 Error Tracking

```
Application Errors
    ↓
Sentry / DataDog
    ├─ Error type and message
    ├─ Stack trace
    ├─ User context
    ├─ Request context
    └─ System metrics at time of error
    ↓
Alerting (Slack / PagerDuty)
    └─ Notify on-call engineer
```

---

## 9. Performance Optimization

### 9.1 Route Calculation Optimization

**Algorithm:** A* pathfinding with heuristics
```
Time Complexity: O(E log V) where E=edges, V=vertices
Space Complexity: O(V)

For Gachibowli dataset:
- ~2000 intersections (V)
- ~5000 street segments (E)
- Average calculation: < 100ms
```

**Caching Strategy:**
```
1. Check if similar route already calculated
2. Return cached result if within tolerance
3. Cache expires after 1 hour
4. Invalidate on new crime data
```

### 9.2 Frontend Optimization

**Mobile App:**
- Code splitting
- Lazy loading of components
- Image optimization
- Offline-first with service workers
- WebP format for images

**Admin Dashboard:**
- Virtual scrolling for large lists
- Debounced search and filters
- Canvas rendering for heatmaps
- Web Workers for heavy computation

### 9.3 Database Optimization

**Indexing Strategy:**
```sql
-- Frequently queried columns
CREATE INDEX idx_routes_user_id ON routes(user_id);
CREATE INDEX idx_sos_alerts_timestamp ON sos_alerts(timestamp);
CREATE INDEX idx_crime_location ON crime_data(latitude, longitude);

-- Composite indexes for common queries
CREATE INDEX idx_crime_bounds ON crime_data(latitude, longitude) 
WHERE date > NOW() - INTERVAL '30 days';
```

**Query Optimization:**
- Connection pooling (PgBouncer)
- Prepared statements
- Query result pagination
- Materialized views for complex aggregations

---

## 10. Disaster Recovery

### 10.1 Backup Strategy

```
Database Backups
├─ Continuous replication (log-based)
├─ Daily full backups (S3 / GCS)
├─ Weekly snapshots (AMI / Disk snapshots)
└─ Retention: 30 days

Configuration Backups
├─ Environment files (encrypted)
├─ Database schemas
├─ API definitions
└─ Deployment configurations
```

### 10.2 High Availability

```
Multi-Region Deployment
├─ Primary Region
│   ├─ Database Master
│   └─ API Servers (3+)
│
└─ Secondary Region (Standby)
    ├─ Database Replica
    └─ API Servers (reduced capacity)

Failover Process:
1. Detect primary region failure
2. Promote secondary database replica
3. Switch DNS to secondary region
4. Scale up secondary API servers
5. Restore from backups if needed
```

---

## 11. Architecture Evolution

### Current State (Version 1.0)
- Monolithic FastAPI backend
- Single PostgreSQL database
- Redis caching layer
- React admin dashboard
- React Native mobile app

### Short Term (Version 1.5 - 6 months)
- Horizontal scaling with load balancer
- Database read replicas
- Multi-region deployment
- Enhanced monitoring and alerting
- Performance optimization

### Medium Term (Version 2.0 - 1 year)
- Microservices architecture
- Event-driven processing (Kafka/RabbitMQ)
- GraphQL API alongside REST
- Real-time analytics pipeline
- ML-based safety predictions

### Long Term (Version 3.0 - 2 years)
- AI-driven route recommendations
- Predictive crime forecasting
- Autonomous emergency response coordination
- Global expansion to multiple cities
- Cross-city safety insights

---

**Last Updated:** March 15, 2026  
**Version:** 1.0.0
