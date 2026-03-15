# SafeRoute Testing Guide

## Overview

SafeRoute follows a comprehensive testing strategy covering unit tests, integration tests, API tests, WebSocket tests, mobile app tests, and load testing. The target coverage is **80%** across all components.

---

## 1. Backend Testing Strategy

### Unit Testing

Unit tests validate individual functions and classes in isolation.

**Location:** `SafeRoute_Backend/tests/test_*.py`

```python
# Example: test_safety_engine.py
import pytest
from services.safety_score_engine import SafetyScoreEngine

class TestSafetyScoreEngine:
    def setup_method(self):
        self.engine = SafetyScoreEngine()
    
    def test_calculate_safety_score_basic(self):
        segment = {
            "crime_density": 0.3,
            "lights_per_100m": 2,
            "crowd_density": 0.5,
            "cctv_count": 3,
            "start_lat": 17.44,
            "start_lon": 78.35,
            "end_lat": 17.45,
            "end_lon": 78.36,
        }
        
        score, impacts = self.engine.calculate_safety_score(segment, hour=14)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1
        assert "crime_base" in impacts
        assert "lighting" in impacts
```

### Integration Testing

Integration tests validate multiple components working together.

```python
# Example: test_route_calculation.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestRouteCalculation:
    def test_full_route_request(self):
        response = client.post(
            "/routes/safest",
            json={
                "start": {"lat": 17.4400, "lng": 78.3480},
                "end": {"lat": 17.4500, "lng": 78.3500},
                "user_id": "test-user-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "route" in data
        assert "distance_meters" in data
        assert "safety_score" in data
        assert len(data["route"]) > 0
```

### API Endpoint Testing

Test all REST API endpoints with various scenarios.

```python
# Example: test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

class TestSOSEndpoint:
    def test_sos_trigger_valid(self):
        response = client.post(
            "/sos/trigger",
            json={
                "user_id": "user123",
                "latitude": 17.44,
                "longitude": 78.35,
                "timestamp": "2026-03-15T14:30:00Z",
                "trigger_type": "button"
            },
            headers={"X-API-Key": "dev-key-change-in-production"}
        )
        assert response.status_code == 200
    
    def test_sos_rate_limiting(self):
        # First alert should succeed
        response1 = client.post("/sos/trigger", json={...})
        assert response1.status_code == 200
        
        # Second alert from same user within cooldown should fail
        response2 = client.post("/sos/trigger", json={...})
        assert response2.status_code == 429  # Too Many Requests
```

### WebSocket Testing

Test real-time WebSocket connections and message handling.

```python
# Example: test_ws.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestWebSocket:
    def test_sos_stream_connection(self):
        with client.websocket_connect("/sos/stream?api_key=admin-key") as websocket:
            # Connection should be accepted
            data = websocket.receive_json()
            assert data is not None
    
    def test_sos_broadcast(self):
        # Simulate admin connected to WebSocket
        with client.websocket_connect("/sos/stream?api_key=admin-key") as websocket:
            # Trigger SOS from another request
            client.post(
                "/sos/trigger",
                json={"user_id": "user123", "latitude": 17.44, "longitude": 78.35, ...}
            )
            
            # Admin should receive broadcast
            data = websocket.receive_json()
            assert data["id"] is not None
            assert data["user_id"] == "user123"
```

### Database Testing

Test database operations with transactions and rollbacks.

```python
# Example: test_familiarity.py
import pytest
from sqlalchemy.orm import Session
from services.familiarity_module import FamiliarityScoreCalculator

class TestFamiliarityScoring:
    def test_familiarity_tracking(self, db: Session):
        calculator = FamiliarityScoreCalculator(db)
        
        # Record travel on segment
        calculator.record_travel("user123", "edge_456")
        calculator.record_travel("user123", "edge_456")
        
        # Get familiarity score
        score = calculator.get_familiarity_score("user123", "edge_456")
        
        assert score > 0.2  # Base score
```

---

## 2. Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov pytest-asyncio httpx
```

### Run All Tests

```bash
# Navigate to backend directory
cd SafeRoute_Backend

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_main.py -v

# Run specific test class
pytest tests/test_main.py::TestHealthEndpoint -v

# Run specific test method
pytest tests/test_main.py::TestHealthEndpoint::test_health_check -v
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html:coverage_html tests/

# View coverage report
open coverage_html/index.html

# Coverage threshold check
pytest --cov=. --cov-fail-under=80 tests/
```

---

## 3. Mobile App Testing

### React Native Testing Tools

**Install dependencies:**

```bash
cd SafeRoute_Native
npm install --save-dev @testing-library/react-native jest-expo
```

### Unit Tests (React Native)

```javascript
// Example: __tests__/MapScreen.test.tsx
import React from 'react';
import { render } from '@testing-library/react-native';
import { MapScreen } from '../src/components/MapScreen';

describe('MapScreen', () => {
  it('renders map component', () => {
    const { getByTestId } = render(<MapScreen />);
    expect(getByTestId('map-container')).toBeTruthy();
  });
});
```

### Integration Tests (Detox)

```bash
# Install Detox
npm install --save-dev detox-cli detox detox-native-driver

# Initialize Detox
detox init -r ios

# Build app for testing
detox build-framework-cache
detox build-app --configuration ios.sim.release

# Run E2E tests
detox test --configuration ios.sim.release
```

**Example E2E Test:**

```javascript
// e2e/firstTest.e2e.js
describe('SOS Button Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should trigger SOS on button press', async () => {
    await element(by.id('sosButton')).tap();
    await waitFor(element(by.text('3'))).toBeVisible().withTimeout(1000);
    await waitFor(element(by.text('Alert Sent'))).toBeVisible().withTimeout(5000);
  });

  it('should show route on map', async () => {
    await element(by.id('destinationInput')).typeText('17.45, 78.35\n');
    await element(by.id('calculateRoute')).tap();
    await waitFor(element(by.id('routePolyline'))).toBeVisible().withTimeout(5000);
  });
});
```

---

## 4. Admin Dashboard Testing

### React Testing Library

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest
```

### Component Tests

```typescript
// Example: src/__tests__/GoogleMapView.test.tsx
import { render, screen } from '@testing-library/react';
import { GoogleMapView } from '../components/GoogleMapView';
import { describe, it, expect } from 'vitest';

describe('GoogleMapView', () => {
  it('renders map container', () => {
    render(<GoogleMapView alerts={[]} activeUserLocations={new Map()} lambda={0.5} />);
    expect(screen.getByTestId('map-container')).toBeInTheDocument();
  });

  it('displays SOS alerts', () => {
    const alerts = [
      {
        id: 1,
        userId: 'user123',
        location: { lat: 17.44, lng: 78.35 },
        timestamp: '2026-03-15T14:30:00Z',
        status: 'active'
      }
    ];
    
    render(<GoogleMapView alerts={alerts} activeUserLocations={new Map()} lambda={0.5} />);
    expect(screen.getByText('user123')).toBeInTheDocument();
  });
});
```

### E2E Testing with Playwright

```bash
npm install --save-dev @playwright/test
```

```typescript
// Example: tests/admin-e2e.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Admin Dashboard', () => {
  test('load heatmap data', async ({ page }) => {
    await page.goto('http://localhost:5173');
    
    // Wait for heatmap to load
    await expect(page.locator('[data-testid="heatmap"]')).toBeVisible();
    
    // Verify SOS alerts visible
    const alerts = await page.locator('[data-testid="sos-alert"]').count();
    expect(alerts).toBeGreaterThan(0);
  });

  it('resolve SOS alert', async ({ page }) => {
    const resolveButton = page.locator('[data-testid="resolve-btn"]:first-child');
    await resolveButton.click();
    
    await expect(page.locator('text=Alert Resolved')).toBeVisible();
  });
});
```

---

## 5. Load Testing

### Using Locust

```bash
pip install locust
```

**`SafeRoute_Backend/tests/load_test.py`:**

```python
from locust import HttpUser, task, between
import random

class SafeRouteUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.api_key = "dev-key-change-in-production"
        self.headers = {"X-API-Key": self.api_key}
    
    @task(3)
    def request_safest_route(self):
        start_lat = 17.440 + random.uniform(-0.01, 0.01)
        start_lng = 78.348 + random.uniform(-0.01, 0.01)
        end_lat = 17.450 + random.uniform(-0.01, 0.01)
        end_lng = 78.358 + random.uniform(-0.01, 0.01)
        
        self.client.post(
            "/routes/safest",
            json={
                "start": {"lat": start_lat, "lng": start_lng},
                "end": {"lat": end_lat, "lng": end_lng},
                "user_id": f"load-test-{random.randint(1, 100)}"
            },
            headers=self.headers
        )
    
    @task(1)
    def request_heatmap(self):
        self.client.get("/routes/heatmap", headers=self.headers)
    
    @task(1)
    def trigger_sos(self):
        self.client.post(
            "/sos/trigger",
            json={
                "user_id": f"load-test-{random.randint(1, 100)}",
                "latitude": 17.44,
                "longitude": 78.35,
                "timestamp": "2026-03-15T14:30:00Z",
                "trigger_type": "button"
            },
            headers=self.headers
        )
```

### Run Load Test

```bash
# Start Locust web UI
locust -f SafeRoute_Backend/tests/load_test.py --host=http://localhost:8000

# Access at http://localhost:8089

# Or run from command line
locust -f load_test.py --host=http://localhost:8000 \
  --users=100 --spawn-rate=10 --run-time=5m --headless
```

### Performance Targets

| Endpoint | Target | Metric |
|----------|--------|--------|
| /routes/safest | < 500ms | P99 latency |
| /routes/fastest | < 500ms | P99 latency |
| /sos/trigger | < 200ms | P99 latency |
| /health | < 50ms | P99 latency |
| Concurrent WebSocket | 1000 | connections |
| Throughput | > 1000 | req/sec |

---

## 6. CI/CD Testing

### GitHub Actions Workflow

**`.github/workflows/test.yml`:**

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      working-directory: SafeRoute_Backend
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      working-directory: SafeRoute_Backend
      run: pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./SafeRoute_Backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node
      uses: actions/setup-node@v3
      with:
        node-version: '20'
    
    - name: Install dependencies
      working-directory: SafeRoute_Admin
      run: npm ci
    
    - name: Run tests
      working-directory: SafeRoute_Admin
      run: npm run test:coverage
    
    - name: Run linter
      working-directory: SafeRoute_Admin
      run: npm run lint
```

---

## 7. Test Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Backend Services | 85% | 75% |
| API Handlers | 90% | 80% |
| Algorithms | 80% | 70% |
| Database Layer | 85% | 75% |
| Admin Dashboard | 75% | 65% |
| Mobile App | 70% | 60% |
| **Overall** | **80%** | **70%** |

---

## 8. Test Data & Fixtures

### Sample Test Data

**`tests/fixtures.py`:**

```python
import pytest
from datetime import datetime, timedelta

@pytest.fixture
def sample_location():
    return {
        "lat": 17.4435,
        "lng": 78.3484
    }

@pytest.fixture
def sample_route_request():
    return {
        "start": {"lat": 17.4400, "lng": 78.3480},
        "end": {"lat": 17.4500, "lng": 78.3500},
        "user_id": "test-user-123"
    }

@pytest.fixture
def sample_sos_alert():
    return {
        "user_id": "user123",
        "latitude": 17.44,
        "longitude": 78.35,
        "timestamp": datetime.utcnow().isoformat(),
        "trigger_type": "button",
        "message": "Help needed"
    }
```

---

## 9. Performance Testing Checklist

- [ ] Route calculation < 500ms (P99)
- [ ] SOS trigger < 200ms (P99)
- [ ] WebSocket latency < 100ms
- [ ] Heatmap generation < 2 seconds
- [ ] Danger zone detection < 1 second
- [ ] Handle 1000 concurrent users
- [ ] Handle 1000 concurrent WebSocket connections
- [ ] Database queries < 100ms (P99)

---

## 10. Debugging Failed Tests

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Run Single Test with Output

```bash
pytest tests/test_main.py::TestHealthEndpoint::test_health_check -v -s
```

### Use PDB Debugger

```python
def test_example():
    result = some_function()
    breakpoint()  # Code execution pauses here
    assert result == expected
```

### Run with Verbose Output

```bash
pytest tests/ -vv --tb=long
```

---

**Last Updated:** March 15, 2026  
**Version:** 1.0.0
