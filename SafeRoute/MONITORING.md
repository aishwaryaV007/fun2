# SafeRoute Monitoring & Observability Guide

Comprehensive guide for monitoring, logging, alerting, and observability in SafeRoute production environments.

---

## 1. Monitoring Stack Overview

SafeRoute uses a multi-layered monitoring approach:

```
┌─────────────────────────────────────────────────────────────┐
│              Application Layer Metrics                       │
│  (Custom metrics, business logic, API performance)           │
└─────────────────────────────────────────────────────────────┘
              ↓ Prometheus / StatsD ↓
┌─────────────────────────────────────────────────────────────┐
│          Infrastructure Metrics & Logs                       │
│  (CPU, Memory, Disk, Network, Container metrics)             │
└─────────────────────────────────────────────────────────────┘
              ↓ Collection & Processing ↓
┌──────────────┬──────────────────┬──────────────────┐
│  Prometheus  │   ELK Stack      │  Cloud Native    │
│  (Metrics)   │  (Logs/Search)   │  (AWS CloudWatch)│
└──────────────┴──────────────────┴──────────────────┘
              ↓ Visualization & Alerting ↓
┌──────────────┬──────────────────┬──────────────────┐
│   Grafana    │    Kibana        │   PagerDuty      │
│ (Dashboards) │ (Log Analysis)   │   (Alerting)     │
└──────────────┴──────────────────┴──────────────────┘
```

---

## 2. Application Metrics

### 2.1 Custom Metrics with Prometheus

**Installation:**

```bash
pip install prometheus-client
```

**FastAPI Integration:**

```python
# services/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI
from fastapi.responses import Response
import time

# Define metrics
route_calculations = Counter(
    'route_calculations_total',
    'Total route calculations',
    ['route_type', 'status']
)

route_calculation_duration = Histogram(
    'route_calculation_seconds',
    'Route calculation duration in seconds',
    ['route_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

sos_alerts_active = Gauge(
    'sos_alerts_active',
    'Number of active SOS alerts'
)

api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_latency = Histogram(
    'api_request_duration_seconds',
    'API request latency in seconds',
    ['method', 'endpoint']
)

websocket_connections = Gauge(
    'websocket_connections',
    'Number of active WebSocket connections'
)

db_query_duration = Histogram(
    'db_query_seconds',
    'Database query duration in seconds',
    ['query_type']
)

# Middleware for API metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    api_requests.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    api_latency.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Usage in Routes:**

```python
@router.post("/routes/safest")
async def calculate_safest_route(request: RouteRequest):
    route_type = "safest"
    
    try:
        with route_calculation_duration.labels(route_type).time():
            # Route calculation logic
            route = await route_service.calculate_safest_route(request)
        
        route_calculations.labels(route_type, "success").inc()
        return route
    
    except Exception as e:
        route_calculations.labels(route_type, "error").inc()
        raise
```

---

### 2.2 Key Metrics to Track

| Metric | Type | Purpose | Threshold |
|--------|------|---------|-----------|
| route_calculations_total | Counter | Total routes calculated | — |
| route_calculation_seconds (P99) | Histogram | Route calc latency | < 500ms |
| sos_alerts_active | Gauge | Active emergency alerts | < 100 |
| api_requests_total | Counter | API request volume | — |
| api_request_duration_seconds (P99) | Histogram | Overall API latency | < 1000ms |
| websocket_connections | Gauge | Active WS connections | < 1000 |
| db_query_seconds (P99) | Histogram | Database latency | < 100ms |
| cache_hit_ratio | Gauge | Cache effectiveness | > 80% |
| error_rate | Counter | Error percentage | < 1% |
| cpu_usage_percent | Gauge | Server CPU utilization | < 70% |
| memory_usage_percent | Gauge | Server memory usage | < 80% |
| disk_usage_percent | Gauge | Disk space usage | < 85% |

---

## 3. Logging Stack

### 3.1 Structured Logging

**Python Implementation:**

```python
# core/logging.py
import logging
import json
from datetime import datetime
import sys

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing."""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

def setup_logging(log_level=logging.INFO):
    """Configure structured logging."""
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Usage
logger = logging.getLogger(__name__)

# Log with context
logger.info(
    "Route calculated",
    extra={
        "user_id": "user123",
        "duration_ms": 245,
        "distance_meters": 1500,
        "safety_score": 0.85
    }
)
```

### 3.2 Request Tracing

```python
# core/tracing.py
import uuid
from fastapi import Request, Response
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class RequestIDMiddleware:
    """Add request ID to all logs."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add to request state
        request.state.request_id = request_id
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response header
        response.headers["X-Request-ID"] = request_id
        
        return response

app.add_middleware(RequestIDMiddleware)
```

---

## 4. ELK Stack Setup (Elasticsearch, Logstash, Kibana)

### 4.1 Docker Compose Configuration

```yaml
# docker-compose-elk.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - saferoute-monitoring

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    environment:
      - "ES_HOSTS=http://elasticsearch:9200"
    ports:
      - "5000:5000/tcp"
      - "5000:5000/udp"
    depends_on:
      - elasticsearch
    networks:
      - saferoute-monitoring

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - saferoute-monitoring

volumes:
  elasticsearch_data:

networks:
  saferoute-monitoring:
    driver: bridge
```

### 4.2 Logstash Configuration

```
# logstash.conf
input {
  tcp {
    port => 5000
    codec => json
  }
  
  udp {
    port => 5000
    codec => json
  }
}

filter {
  # Parse timestamp
  date {
    match => [ "timestamp", "ISO8601" ]
    target => "@timestamp"
  }
  
  # Add environment info
  mutate {
    add_field => {
      "environment" => "${ENVIRONMENT:development}"
      "service" => "saferoute-backend"
    }
  }
}

output {
  elasticsearch {
    hosts => ["${ES_HOSTS:localhost:9200}"]
    index => "saferoute-%{+YYYY.MM.dd}"
  }
}
```

### 4.3 Kibana Dashboards

**Create Dashboard:**
1. Go to http://localhost:5601
2. Create Index Pattern: `saferoute-*`
3. Create visualizations:
   - Request volume over time
   - Error rate by endpoint
   - Route calculation latency
   - SOS alerts timeline
   - Log level distribution

---

## 5. Prometheus & Grafana

### 5.1 Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: "saferoute-backend"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"

  - job_name: "node-exporter"
    static_configs:
      - targets: ["localhost:9100"]

  - job_name: "postgres"
    static_configs:
      - targets: ["localhost:9187"]
```

### 5.2 Alert Rules

```yaml
# alert_rules.yml
groups:
  - name: saferoute_alerts
    interval: 30s
    rules:
      
      # High API latency
      - alert: HighAPILatency
        expr: histogram_quantile(0.99, api_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "High API latency detected"
          description: "99th percentile API latency is {{ $value }}s"
      
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(api_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(api_requests_total[5m]))
          ) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      # Database latency
      - alert: HighDatabaseLatency
        expr: histogram_quantile(0.99, db_query_seconds) > 0.5
        for: 5m
        annotations:
          summary: "High database latency"
      
      # Too many active SOS alerts
      - alert: TooManySOSAlerts
        expr: sos_alerts_active > 100
        for: 1m
        annotations:
          summary: "Spike in SOS alerts"
      
      # WebSocket connection limit
      - alert: WebSocketConnectionLimit
        expr: websocket_connections > 800
        for: 2m
        annotations:
          summary: "Approaching WebSocket connection limit"
      
      # High CPU usage
      - alert: HighCPUUsage
        expr: node_cpu_usage_percent > 80
        for: 5m
      
      # High memory usage
      - alert: HighMemoryUsage
        expr: node_memory_usage_percent > 85
        for: 5m
      
      # Disk space running out
      - alert: LowDiskSpace
        expr: node_disk_usage_percent > 90
        for: 5m
```

### 5.3 Grafana Dashboards

**Main Dashboard JSON:**

```json
{
  "dashboard": {
    "title": "SafeRoute System Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "targets": [
          {
            "expr": "rate(api_requests_total[1m])"
          }
        ]
      },
      {
        "title": "API Latency (P99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, api_request_duration_seconds)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(api_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Active SOS Alerts",
        "targets": [
          {
            "expr": "sos_alerts_active"
          }
        ]
      },
      {
        "title": "Route Calculation Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, route_calculation_seconds)"
          }
        ]
      },
      {
        "title": "Database Query Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, db_query_seconds)"
          }
        ]
      }
    ]
  }
}
```

---

## 6. Sentry Integration (Error Tracking)

### 6.1 FastAPI Integration

```bash
pip install sentry-sdk
```

```python
# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlAlchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(),
        SqlAlchemyIntegration(),
        RedisIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
    environment=os.getenv("ENVIRONMENT", "development"),
    before_send=lambda event, hint: filter_sensitive_data(event),
)
```

### 6.2 Custom Error Reporting

```python
# services/sos_service.py
import sentry_sdk

def handle_sos_alert(alert_data):
    try:
        # SOS processing logic
        process_sos(alert_data)
    except Exception as e:
        # Capture with context
        sentry_sdk.capture_exception(
            e,
            contexts={
                "sos_alert": {
                    "alert_id": alert_data.get("id"),
                    "user_id": alert_data.get("user_id"),
                    "location": alert_data.get("location"),
                }
            },
            tags={
                "alert_type": "sos",
                "severity": "high"
            }
        )
        raise
```

---

## 7. Performance Profiling

### 7.1 Python Profiling with py-spy

```bash
# Install py-spy
pip install py-spy

# Profile running process
py-spy record -o profile.svg --pid $(pgrep -f "uvicorn main:app")

# CPU profiling
py-spy dump --pid $(pgrep -f "uvicorn main:app")
```

### 7.2 Database Query Analysis

```python
# core/db.py
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    
    if total > 0.1:  # Log slow queries (> 100ms)
        logger.warning(
            f"Slow query detected ({total:.3f}s): {statement}",
            extra={
                "duration_ms": total * 1000,
                "query": statement[:200],  # First 200 chars
            }
        )
```

---

## 8. Health Checks

### 8.1 Liveness and Readiness Probes

```python
@app.get("/health")
async def health_check():
    """Liveness check - is app running?"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check - can app handle traffic?"""
    try:
        # Check database
        db.execute(text("SELECT 1"))
        
        # Check cache
        if redis_client:
            redis_client.ping()
        
        # Check external dependencies
        maps_api.check_connection()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "ok",
                "cache": "ok",
                "maps_api": "ok"
            }
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 503
```

### 8.2 Kubernetes Probe Configuration

```yaml
# deployment.yaml
spec:
  containers:
    - name: saferoute-backend
      livenessProbe:
        httpGet:
          path: /health
          port: 8000
        initialDelaySeconds: 30
        periodSeconds: 10
        timeoutSeconds: 5
        failureThreshold: 3
      
      readinessProbe:
        httpGet:
          path: /ready
          port: 8000
        initialDelaySeconds: 10
        periodSeconds: 5
        timeoutSeconds: 3
        failureThreshold: 2
```

---

## 9. Alerting Strategy

### 9.1 Alert Severity Levels

| Level | Response Time | Examples |
|-------|---------------|----------|
| **Critical** | Immediate (< 5 min) | Database down, all requests failing, security breach |
| **High** | Urgent (< 15 min) | > 10% error rate, > 2s latency, data loss |
| **Medium** | Standard (< 1 hour) | > 5% error rate, cache miss, slow queries |
| **Low** | Normal (< 4 hours) | Approaching limits, deprecation warnings |

### 9.2 Alert Routing

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster']
  routes:
    # Critical alerts
    - match:
        severity: critical
      receiver: 'pagerduty_critical'
      continue: true
      group_wait: 0s
      group_interval: 1m
      repeat_interval: 30m
    
    # High priority
    - match:
        severity: high
      receiver: 'slack_high_priority'
      group_wait: 5m
      group_interval: 10m
    
    # Medium priority
    - match:
        severity: medium
      receiver: 'slack_medium_priority'
      group_wait: 15m
      group_interval: 30m

receivers:
  - name: 'pagerduty_critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
  
  - name: 'slack_high_priority'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK'
        channel: '#alerts-high'
  
  - name: 'slack_medium_priority'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK'
        channel: '#alerts'
```

---

## 10. Production Monitoring Checklist

### Daily Checks

- [ ] Error rate < 1%
- [ ] API latency P99 < 1s
- [ ] Database latency P99 < 100ms
- [ ] No critical alerts firing
- [ ] All services healthy
- [ ] Disk usage < 85%
- [ ] Memory usage < 80%

### Weekly Checks

- [ ] Review error trends
- [ ] Analyze slow query logs
- [ ] Check backup status
- [ ] Review disk growth rate
- [ ] Audit access logs
- [ ] Test alert notification channels

### Monthly Checks

- [ ] Disaster recovery drill
- [ ] Database optimization review
- [ ] Performance trend analysis
- [ ] Security audit
- [ ] Dependency update check
- [ ] Capacity planning review

---

## 11. Runbooks

### When API latency is high (P99 > 1s)

1. Check current traffic volume (requests/sec)
2. Check database query latency
3. Check cache hit ratio
4. Check CPU and memory usage
5. Review error logs for exceptions
6. Check external API response times (Maps API)
7. Scale horizontally if load-related
8. Optimize database queries if query-related

### When error rate spikes

1. Check error logs in Kibana
2. Identify affected endpoint(s)
3. Check if database is reachable
4. Check if external services are reachable
5. Verify recent deployments
6. Check rate limiter status
7. Scale if under DDoS

### When SOS alerts spike

1. Check if legitimate spike (incident in area)
2. Verify alert processing is working
3. Check database capacity
4. Check WebSocket connection limits
5. Verify emergency contact notifications working
6. Review responder assignment logic

---

**Last Updated:** March 15, 2026  
**Version:** 1.0.0
