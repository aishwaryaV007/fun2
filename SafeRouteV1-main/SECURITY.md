# SafeRoute Security Guidelines

## Overview

SafeRoute implements multiple layers of security to protect user data, system integrity, and prevent unauthorized access. This document outlines the security architecture, best practices, and implementation details.

---

## 1. Authentication & Authorization

### API Key Authentication

All sensitive endpoints require API key validation via the `X-API-Key` header.

**Implementation:**
- Location: `SafeRoute_Backend/core/security.py`
- Two-tier API key system:
  - `SAFETY_API_KEY`: General API access (route calculation, SOS submission)
  - `ADMIN_API_KEY`: Administrative access (analytics, alert management)

**Usage:**
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/routes/safest
```

**Configuration:**
```env
SAFETY_API_KEY=your-secret-key-here
ADMIN_API_KEY=your-admin-key-here
ENFORCE_ADMIN_API_KEY=true  # Enable in production
```

### JWT Authentication (Future Implementation)

For production deployments with multiple admin users, implement JWT tokens:

```python
# Example JWT implementation (add to core/security.py)
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt

security = HTTPBearer()

async def verify_jwt_token(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=403, detail="Invalid token")
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")
```

---

## 2. HTTPS & WSS (Transport Security)

### Production Requirements

**Always use HTTPS/WSS in production:**

```bash
# HTTPS with Let's Encrypt
curl https://api.saferoute.example.com/health

# WSS (Secure WebSocket)
wss://api.saferoute.example.com/sos/stream
```

### Configuration

#### Backend (FastAPI + Uvicorn)

```bash
# Run with SSL certificates
uvicorn main:app --host 0.0.0.0 --port 443 \
  --ssl-keyfile=/path/to/key.pem \
  --ssl-certfile=/path/to/cert.pem
```

#### Docker Deployment

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - BACKEND_PORT=443
    ports:
      - "443:443"
    volumes:
      - ./certs:/app/certs:ro
```

---

## 3. CORS (Cross-Origin Resource Sharing)

### Configuration

CORS is configured to prevent unauthorized cross-origin access:

**Location:** `SafeRoute_Backend/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,  # ["http://localhost:3000", ...]
    allow_origin_regex=CORS_ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)
```

### Environment Configuration

```env
# Development
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000
CORS_ALLOWED_ORIGIN_REGEX=.*localhost.*

# Production
CORS_ALLOWED_ORIGINS=https://saferoute.example.com,https://admin.saferoute.example.com
CORS_ALLOWED_ORIGIN_REGEX=
```

---

## 4. Rate Limiting

### Implementation

Rate limiting prevents abuse, DDoS attacks, and excessive resource consumption.

**Location:** `SafeRoute_Backend/services/rate_limiter.py`

```python
from cachetools import TTLCache

# Per-endpoint rate limiting
ROUTE_RATE_LIMIT = TTLCache(
    maxsize=1000,
    ttl=60,  # 60-second window
)

# Example: 100 requests per 60 seconds per IP
MAX_REQUESTS_PER_WINDOW = 100
```

### Endpoint Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| /routes/safest | 100 | 60 sec |
| /routes/fastest | 100 | 60 sec |
| /sos/trigger | 10 | 300 sec |
| /crime/report | 50 | 300 sec |
| /admin/* | 1000 | 60 sec |

### Configuration

```env
ROUTE_RATE_LIMIT_REQUESTS=100
ROUTE_RATE_LIMIT_WINDOW_SECONDS=60

SOS_RATE_LIMIT_REQUESTS=10
SOS_RATE_LIMIT_WINDOW_SECONDS=300

ADMIN_READ_RATE_LIMIT_REQUESTS=1000
ADMIN_READ_RATE_LIMIT_WINDOW_SECONDS=60
```

---

## 5. Data Privacy & Protection

### Local Storage (Privacy-First)

**No user location data is transmitted to external servers.**

All sensitive data is stored locally:

1. **User Travel History** - `safe_routes.db` (SQLite)
   - Stored only on device/server
   - Never transmitted to cloud
   - User can request data deletion

2. **SOS Alerts** - `sos_alerts.db` (SQLite)
   - Stored on server only
   - Admin accessible only with API key
   - Historical retention: 90 days (configurable)

3. **Crime Reports** - `crime_reports.db` (SQLite)
   - Aggregated data only
   - Individual locations anonymized
   - Used only for heatmap generation

### GDPR Compliance

**User Data Rights:**

```python
# Example: User data export endpoint
@app.get("/user/{user_id}/export")
async def export_user_data(user_id: str, api_key: str = Depends(verify_api_key)):
    """Export all user personal data (GDPR Article 20)"""
    data = {
        "user_id": user_id,
        "travel_history": get_user_travel_history(user_id),
        "sos_alerts": get_user_sos_alerts(user_id),
    }
    return data

# Example: User data deletion endpoint
@app.delete("/user/{user_id}/data")
async def delete_user_data(user_id: str, api_key: str = Depends(verify_api_key)):
    """Delete all user personal data (GDPR Article 17 - Right to be Forgotten)"""
    delete_user_travel_history(user_id)
    delete_user_sos_alerts(user_id)
    return {"status": "deleted"}
```

### CCPA Compliance

California Consumer Privacy Act requirements:

- ✅ Right to know what personal information is collected
- ✅ Right to delete personal information
- ✅ Right to opt-out of sale or sharing
- ✅ Right to non-discrimination for exercising privacy rights

**Implementation:** Same as GDPR endpoints above.

---

## 6. Input Validation & Sanitization

### Pydantic Validation

All API requests are validated using Pydantic models:

```python
# Location validation
class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)  # Latitude bounds
    lng: float = Field(ge=-180, le=180)  # Longitude bounds

# Request validation
class RouteRequest(BaseModel):
    start: Location
    end: Location
    user_id: str = Field(min_length=1, max_length=128)
    time: str = Field(default=None, regex=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
```

### SQL Injection Prevention

**Never use raw SQL queries.** Always use SQLAlchemy ORM:

```python
# ❌ VULNERABLE (DO NOT USE)
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ SECURE (USE THIS)
from sqlalchemy import select
stmt = select(UserProfile).where(UserProfile.user_id == user_id)
user = session.execute(stmt).scalar_one_or_none()
```

### Coordinate Validation

All coordinates are validated against Gachibowli bounds:

```python
def coords_in_bounds(lat: float, lng: float, bounds: dict) -> bool:
    """Ensure coordinates are within service area"""
    return (
        bounds["min_lat"] <= lat <= bounds["max_lat"] and
        bounds["min_lng"] <= lng <= bounds["max_lng"]
    )

# Validation in every endpoint
if not coords_in_bounds(lat, lng, BOUNDS):
    raise HTTPException(status_code=400, detail="Coordinates out of service area")
```

---

## 7. WebSocket Security

### Connection Authentication

WebSocket connections require API key validation:

```python
@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket, api_key: str = Query(...)):
    # Validate API key before accepting connection
    if not validate_api_key(api_key):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await websocket.accept()
    # ... connection handling
```

### Message Validation

All WebSocket messages are validated:

```python
try:
    data = await websocket.receive_json()
    # Validate message schema
    validated_data = SomeModel(**data)
    # Process validated data
except json.JSONDecodeError:
    await websocket.send_json({"error": "Invalid JSON"})
except ValidationError:
    await websocket.send_json({"error": "Invalid message format"})
```

### Connection Limits

```env
WEBSOCKET_MAX_CONNECTIONS=1000
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_HEARTBEAT_TIMEOUT=60
```

---

## 8. Secrets Management

### Never Commit Secrets

**`.gitignore` rules:**

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Secret keys
*.key
*.pem
secrets/

# API keys
api_keys.txt
credentials.json
```

### Environment Variables

Store all secrets in environment variables, never in code:

```python
# ✅ CORRECT
API_KEY = os.getenv("SAFETY_API_KEY")

# ❌ WRONG
API_KEY = "hardcoded-secret-key"
```

### Secret Rotation

```bash
# Rotate API keys regularly (monthly recommended)
# Update .env and restart servers
SAFETY_API_KEY=new-key-$(date +%s)
```

### Production Secret Storage

**Recommended services:**

- **AWS Secrets Manager**: Store and rotate secrets
- **HashiCorp Vault**: Enterprise secret management
- **Azure Key Vault**: Azure-native secret storage
- **Google Cloud Secret Manager**: GCP-native solution

Example with AWS Secrets Manager:

```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

API_KEY = get_secret('saferoute/api-key')
```

---

## 9. Logging & Monitoring

### Secure Logging

Never log sensitive information:

```python
# ❌ INSECURE (logs API key)
logger.info(f"API request: {request.headers}")

# ✅ SECURE (redacts sensitive fields)
safe_headers = {k: v if k != "X-API-Key" else "***" for k, v in request.headers.items()}
logger.info(f"API request: {safe_headers}")
```

### Structured Logging

```python
import logging
import json

# JSON logging for better parsing
logger = logging.getLogger(__name__)

def log_event(event_type, details, user_id=None):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "user_id": user_id,
        "details": details,
    }
    logger.info(json.dumps(log_entry))

# Usage
log_event("SOS_TRIGGERED", {"location": (17.44, 78.35)}, user_id="user123")
```

### Monitoring Alerts

Monitor critical security events:

```python
# Alert on failed login attempts
failed_attempts[ip] += 1
if failed_attempts[ip] > 5:
    alert_security_team(f"Brute force attempt from {ip}")

# Alert on unusual API usage
if requests_per_minute > THRESHOLD:
    alert_security_team(f"Rate limit exceeded from {ip}")

# Alert on unauthorized access attempts
if status_code == 403:
    alert_security_team(f"Unauthorized access attempt: {endpoint}")
```

---

## 10. Dependency Security

### Vulnerability Scanning

Regularly scan dependencies for vulnerabilities:

```bash
# Install safety
pip install safety

# Scan requirements.txt
safety check

# Run in CI/CD pipeline
safety check --json > security-report.json
```

### Dependency Updates

Keep dependencies updated:

```bash
# Check outdated packages
pip list --outdated

# Update all packages
pip install --upgrade -r requirements.txt

# Use tools like Dependabot (GitHub)
# or Snyk for continuous dependency monitoring
```

### Pinned Versions

Always pin dependency versions in production:

```requirements.txt
# ✅ Pinned versions (production)
fastapi==0.115.6
pydantic==2.9.2

# ❌ Floating versions (development only)
fastapi==0.11*
pydantic==2.9*
```

---

## 11. Incident Response

### Security Contact

Establish a security contact for vulnerability reports:

```
Security issues should be reported to: security@saferoute.example.com
```

### Incident Response Plan

1. **Detection**: Monitor logs and alerts
2. **Analysis**: Determine scope and severity
3. **Containment**: Isolate affected systems
4. **Eradication**: Fix the vulnerability
5. **Recovery**: Restore normal operations
6. **Post-Mortem**: Document and improve

### Vulnerability Disclosure

```markdown
# Responsible Disclosure Policy

We appreciate your effort to improve SafeRoute's security.

## Reporting Process

1. Email security@saferoute.example.com with:
   - Vulnerability description
   - Steps to reproduce
   - Impact assessment
   - Proposed fix (optional)

2. We will acknowledge receipt within 24 hours

3. We will provide a timeline for fix and disclosure

4. You will be credited (if desired) in security advisory
```

---

## 12. Production Deployment Checklist

- [ ] ✅ SSL/TLS certificates installed and valid
- [ ] ✅ HTTPS/WSS enforced (redirect HTTP to HTTPS)
- [ ] ✅ CORS configured for production domains only
- [ ] ✅ API keys rotated and strong (32+ characters)
- [ ] ✅ Database encrypted at rest
- [ ] ✅ Database backups encrypted
- [ ] ✅ Rate limiting enabled on all endpoints
- [ ] ✅ API key authentication enforced
- [ ] ✅ Logging configured with redaction
- [ ] ✅ Monitoring and alerting active
- [ ] ✅ Secrets not in version control
- [ ] ✅ Dependencies scanned for vulnerabilities
- [ ] ✅ Security headers configured
- [ ] ✅ CORS, CSP, X-Frame-Options set
- [ ] ✅ Database admin credentials rotated
- [ ] ✅ Backup and disaster recovery tested
- [ ] ✅ Security audit completed
- [ ] ✅ Incident response plan documented

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/advanced/security/)
- [GDPR Compliance](https://gdpr-info.eu/)
- [CCPA Compliance](https://www.ccpa.org/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

**Last Updated:** March 15, 2026  
**Version:** 1.0.0  
**Maintained By:** SafeRoute Security Team
