# SafeRoute API Documentation

Complete API reference for SafeRoute backend services. All endpoints require authentication via API key or JWT token.

## Base URL

- **Development:** `http://localhost:8000`
- **Production:** `https://api.saferoute.example.com` (configure in environment)

## Authentication

### API Key Authentication

All requests must include API key in headers:

```bash
curl -H "X-API-Key: your-api-key" https://api.saferoute.example.com/routes/safest
```

### JWT Authentication (Future)

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  https://api.saferoute.example.com/user/profile
```

---

## 1. Health & Status

### Get System Health

```
GET /health
```

**Description:** Check if the API is running and all critical services are operational.

**Authentication:** None

**Response (200 OK):**

```json
{
  "status": "ok",
  "timestamp": "2026-03-15T14:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "maps_api": "ok",
    "cache": "connected"
  }
}
```

**Response (503 Service Unavailable):**

```json
{
  "status": "degraded",
  "timestamp": "2026-03-15T14:30:00Z",
  "error": "Database connection failed",
  "services": {
    "database": "down",
    "maps_api": "ok",
    "cache": "disconnected"
  }
}
```

---

## 2. Routes

### Calculate Safest Route

```
POST /routes/safest
```

**Description:** Find the safest route between two points, optimizing for security metrics.

**Authentication:** Required (API Key or JWT)

**Request Body:**

```json
{
  "start": {
    "lat": 17.4400,
    "lng": 78.3480
  },
  "end": {
    "lat": 17.4500,
    "lng": 78.3500
  },
  "user_id": "user123",
  "departure_time": "2026-03-15T14:30:00Z",
  "avoid_areas": [
    {
      "lat": 17.44,
      "lng": 78.35,
      "radius_meters": 100
    }
  ]
}
```

**Response (200 OK):**

```json
{
  "route": [
    {
      "lat": 17.4400,
      "lng": 78.3480,
      "segment_index": 0
    },
    {
      "lat": 17.4410,
      "lng": 78.3490,
      "segment_index": 1
    }
  ],
  "distance_meters": 1500,
  "estimated_time_seconds": 900,
  "safety_score": 0.85,
  "danger_zones": [
    {
      "location": {"lat": 17.4420, "lng": 78.3495},
      "severity": "medium",
      "type": "crime_hotspot",
      "distance_meters": 50
    }
  ],
  "safety_breakdown": {
    "crime_density": 0.30,
    "lighting": 0.85,
    "crowd_density": 0.60,
    "cctv_coverage": 0.70
  },
  "route_id": "route_123abc",
  "generated_at": "2026-03-15T14:30:00Z"
}
```

**Error (400 Bad Request):**

```json
{
  "detail": "Invalid coordinates: latitude must be between -90 and 90"
}
```

**Error (429 Too Many Requests):**

```json
{
  "detail": "Rate limit exceeded: 100 requests per minute",
  "retry_after": 45
}
```

---

### Calculate Fastest Route

```
POST /routes/fastest
```

**Description:** Find the fastest route between two points (time-optimized).

**Authentication:** Required (API Key or JWT)

**Request Body:**

```json
{
  "start": {"lat": 17.4400, "lng": 78.3480},
  "end": {"lat": 17.4500, "lng": 78.3500},
  "user_id": "user123",
  "avoid_areas": []
}
```

**Response (200 OK):**

```json
{
  "route": [...],
  "distance_meters": 1200,
  "estimated_time_seconds": 600,
  "safety_score": 0.72,
  "route_id": "route_456def",
  "generated_at": "2026-03-15T14:30:00Z"
}
```

---

### Compare Multiple Routes

```
POST /routes/compare
```

**Description:** Calculate multiple route options with different criteria (safest, fastest, balanced).

**Authentication:** Required (API Key or JWT)

**Request Body:**

```json
{
  "start": {"lat": 17.4400, "lng": 78.3480},
  "end": {"lat": 17.4500, "lng": 78.3500},
  "user_id": "user123",
  "include_options": ["safest", "fastest", "balanced"]
}
```

**Response (200 OK):**

```json
{
  "routes": {
    "safest": {
      "route": [...],
      "distance_meters": 1500,
      "estimated_time_seconds": 900,
      "safety_score": 0.85
    },
    "fastest": {
      "route": [...],
      "distance_meters": 1200,
      "estimated_time_seconds": 600,
      "safety_score": 0.72
    },
    "balanced": {
      "route": [...],
      "distance_meters": 1350,
      "estimated_time_seconds": 750,
      "safety_score": 0.78
    }
  },
  "generated_at": "2026-03-15T14:30:00Z"
}
```

---

### Get Route Heatmap

```
GET /routes/heatmap
```

**Description:** Get heatmap data showing danger zones and safety levels across the map.

**Authentication:** Required (API Key or JWT)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bounds` | string | yes | Bounding box as "lat_min,lng_min,lat_max,lng_max" |
| `metric` | string | no | One of: "crime", "lighting", "crowd", "cctv" (default: "crime") |
| `zoom_level` | integer | no | Map zoom level (affects granularity, 10-20) |

**Example:**

```bash
GET /routes/heatmap?bounds=17.43,78.34,17.45,78.36&metric=crime&zoom_level=15
```

**Response (200 OK):**

```json
{
  "heatmap_grid": [
    {
      "cell_id": "grid_1",
      "center": {"lat": 17.4350, "lng": 78.3450},
      "severity_score": 0.75,
      "metric_value": 0.30,
      "data_points": 245,
      "last_updated": "2026-03-15T14:00:00Z"
    }
  ],
  "bounds": {
    "min": {"lat": 17.43, "lng": 78.34},
    "max": {"lat": 17.45, "lng": 78.36}
  },
  "metric": "crime",
  "generated_at": "2026-03-15T14:30:00Z"
}
```

---

### Get Familiarity Score

```
GET /routes/familiarity/{user_id}/{edge_id}
```

**Description:** Get how familiar a user is with a particular route segment.

**Authentication:** Required (API Key or JWT)

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | path | User ID |
| `edge_id` | path | Route edge ID |

**Response (200 OK):**

```json
{
  "user_id": "user123",
  "edge_id": "edge_456",
  "familiarity_score": 0.65,
  "travel_count": 12,
  "last_traveled": "2026-03-14T18:30:00Z",
  "average_time_of_day": "evening",
  "comfort_level": "comfortable"
}
```

---

## 3. SOS (Emergency)

### Trigger SOS Alert

```
POST /sos/trigger
```

**Description:** Trigger an emergency SOS alert to notify responders and contacts.

**Authentication:** Required (API Key or JWT)

**Rate Limit:** 10 requests per 300 seconds per user

**Request Body:**

```json
{
  "user_id": "user123",
  "latitude": 17.4400,
  "longitude": 78.3480,
  "timestamp": "2026-03-15T14:30:00Z",
  "trigger_type": "button",
  "message": "Help needed",
  "severity": "high",
  "emergency_contacts": [
    {
      "name": "Mom",
      "phone": "+91-9876543210",
      "relationship": "parent"
    }
  ]
}
```

**Response (200 OK):**

```json
{
  "alert_id": "sos_789xyz",
  "status": "active",
  "timestamp": "2026-03-15T14:30:00Z",
  "location": {"lat": 17.4400, "lng": 78.3480},
  "responders_notified": 3,
  "contacts_notified": 1,
  "emergency_number": "112"
}
```

**Error (429 Too Many Requests):**

```json
{
  "detail": "SOS rate limit exceeded. Maximum 10 alerts per 5 minutes.",
  "retry_after": 180,
  "next_allowed": "2026-03-15T14:35:00Z"
}
```

---

### Get SOS Alert Details

```
GET /sos/{alert_id}
```

**Description:** Get details of a specific SOS alert.

**Authentication:** Required (API Key or JWT)

**Response (200 OK):**

```json
{
  "alert_id": "sos_789xyz",
  "user_id": "user123",
  "status": "resolved",
  "location": {"lat": 17.4400, "lng": 78.3480},
  "timestamp": "2026-03-15T14:30:00Z",
  "resolved_at": "2026-03-15T14:35:00Z",
  "responders": [
    {
      "responder_id": "resp_001",
      "type": "police",
      "status": "en_route",
      "eta_seconds": 300
    }
  ],
  "contacts_notified": [
    {
      "contact_id": "contact_001",
      "name": "Mom",
      "status": "notified",
      "notified_at": "2026-03-15T14:30:15Z"
    }
  ]
}
```

---

### List Active SOS Alerts

```
GET /sos/active
```

**Description:** Get list of all active SOS alerts (admin only).

**Authentication:** Required (Admin API Key or JWT with admin role)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum results (default: 100) |
| `offset` | integer | Pagination offset (default: 0) |
| `severity` | string | Filter by severity: "low", "medium", "high" |

**Response (200 OK):**

```json
{
  "alerts": [
    {
      "alert_id": "sos_789xyz",
      "user_id": "user123",
      "status": "active",
      "location": {"lat": 17.4400, "lng": 78.3480},
      "severity": "high",
      "timestamp": "2026-03-15T14:30:00Z",
      "responders_en_route": 2
    }
  ],
  "total_count": 42,
  "limit": 100,
  "offset": 0
}
```

---

### Resolve SOS Alert

```
POST /sos/{alert_id}/resolve
```

**Description:** Mark an SOS alert as resolved.

**Authentication:** Required (Admin API Key or JWT with admin role)

**Request Body:**

```json
{
  "resolved_by": "responder_001",
  "resolution_type": "emergency_services_arrived",
  "notes": "Police arrived and situation handled"
}
```

**Response (200 OK):**

```json
{
  "alert_id": "sos_789xyz",
  "status": "resolved",
  "resolved_at": "2026-03-15T14:35:00Z",
  "resolution_type": "emergency_services_arrived"
}
```

---

## 4. Users

### Get User Profile

```
GET /user/profile
```

**Description:** Get authenticated user's profile information.

**Authentication:** Required (JWT with user ID)

**Response (200 OK):**

```json
{
  "user_id": "user123",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+91-9876543210",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2026-03-15T14:30:00Z",
  "preferences": {
    "route_preference": "safety",
    "notifications_enabled": true,
    "emergency_contacts": 2,
    "share_location": true
  },
  "safety_metrics": {
    "sos_triggered": 1,
    "routes_taken": 156,
    "familiarity_score": 0.72
  }
}
```

---

### Update User Profile

```
PUT /user/profile
```

**Description:** Update user profile information.

**Authentication:** Required (JWT with user ID)

**Request Body:**

```json
{
  "name": "Jane Smith",
  "phone": "+91-9876543211",
  "preferences": {
    "route_preference": "balanced",
    "notifications_enabled": true
  }
}
```

**Response (200 OK):**

```json
{
  "user_id": "user123",
  "name": "Jane Smith",
  "updated_at": "2026-03-15T14:32:00Z",
  "message": "Profile updated successfully"
}
```

---

### Add Emergency Contact

```
POST /user/emergency-contacts
```

**Description:** Add an emergency contact to user's profile.

**Authentication:** Required (JWT with user ID)

**Request Body:**

```json
{
  "name": "Dad",
  "phone": "+91-9876543212",
  "email": "dad@example.com",
  "relationship": "parent"
}
```

**Response (200 OK):**

```json
{
  "contact_id": "contact_002",
  "user_id": "user123",
  "name": "Dad",
  "phone": "+91-9876543212",
  "created_at": "2026-03-15T14:30:00Z"
}
```

---

### Get User Travel History

```
GET /user/history
```

**Description:** Get user's recent route and travel history.

**Authentication:** Required (JWT with user ID)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum results (default: 50) |
| `days` | integer | Last N days (default: 30) |

**Response (200 OK):**

```json
{
  "history": [
    {
      "journey_id": "journey_001",
      "start": {"lat": 17.4400, "lng": 78.3480},
      "end": {"lat": 17.4500, "lng": 78.3500},
      "distance_meters": 1500,
      "duration_seconds": 900,
      "timestamp": "2026-03-15T14:30:00Z",
      "safety_score": 0.85,
      "sos_triggered": false
    }
  ],
  "total_journeys": 156,
  "average_safety_score": 0.78,
  "dangerous_routes": 3
}
```

---

## 5. Active Users (Real-time)

### Get Active Users

```
GET /active-users
```

**Description:** Get list of currently active users on the map.

**Authentication:** Required (API Key or JWT)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `bounds` | string | Bounding box "lat_min,lng_min,lat_max,lng_max" |
| `limit` | integer | Maximum results (default: 100) |

**Response (200 OK):**

```json
{
  "active_users": [
    {
      "user_id": "user123",
      "location": {"lat": 17.4400, "lng": 78.3480},
      "timestamp": "2026-03-15T14:30:00Z",
      "status": "traveling",
      "danger_level": "safe",
      "destination": {"lat": 17.4500, "lng": 78.3500}
    }
  ],
  "total_active": 42,
  "last_updated": "2026-03-15T14:30:00Z"
}
```

---

### Stream Active Users (WebSocket)

```
WebSocket GET /active-users/stream?api_key=your-api-key
```

**Description:** Real-time stream of active user locations.

**Authentication:** Required (API Key as query parameter)

**Message Format (Server to Client):**

```json
{
  "type": "user_update",
  "user_id": "user123",
  "location": {"lat": 17.4400, "lng": 78.3480},
  "timestamp": "2026-03-15T14:30:00Z",
  "status": "traveling"
}
```

```json
{
  "type": "user_left",
  "user_id": "user456",
  "timestamp": "2026-03-15T14:30:15Z"
}
```

---

## 6. Crime Data

### Get Crime Statistics

```
GET /crime/statistics
```

**Description:** Get crime statistics for a geographic area.

**Authentication:** Required (API Key or JWT)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `bounds` | string | Bounding box "lat_min,lng_min,lat_max,lng_max" |
| `crime_type` | string | Optional filter: "theft", "assault", "robbery", "all" |
| `days` | integer | Last N days (default: 30) |

**Response (200 OK):**

```json
{
  "statistics": {
    "total_incidents": 156,
    "crime_density": 0.35,
    "hot_zones": 5,
    "trend": "increasing"
  },
  "by_type": {
    "theft": {
      "count": 89,
      "percentage": 57,
      "trend": "stable"
    },
    "assault": {
      "count": 45,
      "percentage": 29,
      "trend": "increasing"
    },
    "robbery": {
      "count": 22,
      "percentage": 14,
      "trend": "decreasing"
    }
  },
  "time_analysis": {
    "peak_hours": ["19:00", "20:00", "21:00"],
    "safest_hours": ["06:00", "07:00", "08:00"],
    "dangerous_days": ["Friday", "Saturday"]
  }
}
```

---

## 7. Admin Dashboard

### Get Dashboard Metrics

```
GET /admin/metrics
```

**Description:** Get overall system metrics for admin dashboard.

**Authentication:** Required (Admin API Key or JWT with admin role)

**Response (200 OK):**

```json
{
  "system_metrics": {
    "active_users": 156,
    "total_users": 5234,
    "sos_alerts_today": 12,
    "average_response_time": 240,
    "routes_calculated_today": 8934
  },
  "safety_metrics": {
    "average_area_safety": 0.72,
    "danger_zones": 18,
    "crime_reports_today": 34,
    "sos_success_rate": 0.94
  },
  "technical_metrics": {
    "api_uptime": 0.9995,
    "avg_response_time_ms": 245,
    "error_rate": 0.0005,
    "websocket_connections": 342
  }
}
```

---

### Get SOS Stream (WebSocket)

```
WebSocket GET /sos/stream?api_key=admin-key
```

**Description:** Real-time stream of SOS alerts for admin dashboard.

**Authentication:** Required (Admin API Key as query parameter)

**Message Format:**

```json
{
  "type": "sos_alert",
  "alert_id": "sos_789xyz",
  "user_id": "user123",
  "location": {"lat": 17.4400, "lng": 78.3480},
  "severity": "high",
  "timestamp": "2026-03-15T14:30:00Z"
}
```

---

## Error Responses

### Standard Error Format

All errors follow this format:

```json
{
  "detail": "Error message",
  "error_code": "INVALID_REQUEST",
  "timestamp": "2026-03-15T14:30:00Z",
  "request_id": "req_abc123"
}
```

### Common HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Invalid coordinates or parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal server error |
| 503 | Service Unavailable | Service temporarily down |

---

## Rate Limiting

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1710522600
```

### Rate Limits by Endpoint

| Endpoint | Limit | Window |
|----------|-------|--------|
| /routes/safest | 100 | 1 minute |
| /routes/fastest | 100 | 1 minute |
| /sos/trigger | 10 | 5 minutes |
| /user/profile | 1000 | 1 minute |
| /active-users | 100 | 1 minute |

---

## Pagination

For endpoints returning lists:

```bash
GET /sos/active?limit=20&offset=40
```

**Response includes:**

```json
{
  "data": [...],
  "pagination": {
    "limit": 20,
    "offset": 40,
    "total": 156,
    "pages": 8,
    "current_page": 3
  }
}
```

---

## Data Types

### Coordinate Object

```json
{
  "lat": 17.4435,
  "lng": 78.3484
}
```

### Location (with timestamp)

```json
{
  "lat": 17.4435,
  "lng": 78.3484,
  "timestamp": "2026-03-15T14:30:00Z"
}
```

### BoundingBox

```json
{
  "min": {"lat": 17.43, "lng": 78.34},
  "max": {"lat": 17.45, "lng": 78.36}
}
```

---

## Live API Playground

Interactive API documentation available at:

- **Development:** `http://localhost:8000/docs` (Swagger UI)
- **Development:** `http://localhost:8000/redoc` (ReDoc)
- **Production:** `https://api.saferoute.example.com/docs`

---

**Last Updated:** March 15, 2026  
**API Version:** 1.0.0  
**Base URL:** `/` (relative to host)
