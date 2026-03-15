import requests
import json
import logging
logging.basicConfig(level=logging.INFO)

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, json_data=None):
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}")
        else:
            response = requests.post(f"{BASE_URL}{url}", json=json_data)
        
        logging.info(f"{name}: {response.status_code}")
        if response.status_code != 200:
            logging.error(f"Response: {response.text}")
            return False
        return True
    except Exception as e:
        logging.error(f"{name} failed: {e}")
        return False

success = True

# Heatmap
success &= test_endpoint("GET /heatmap", "GET", "/heatmap")

# Server Info
success &= test_endpoint("GET /server-info", "GET", "/server-info")

# Safest route
route_data = {
    "start": {"lat": 17.4267, "lng": 78.3368},
    "end": {"lat": 17.4455, "lng": 78.3317},
    "time": "14:00"
}
success &= test_endpoint("POST /safest_route (legacy)", "POST", "/safest_route", route_data)
success &= test_endpoint("POST /routes/safest (new)", "POST", "/routes/safest", route_data)

# SOS trigger
sos_data = {
    "user_id": "test_user_1",
    "latitude": 17.4300,
    "longitude": 78.3400,
    "timestamp": "2026-03-11T12:00:00Z"
}
success &= test_endpoint("POST /sos_alert (legacy)", "POST", "/sos_alert", sos_data)
success &= test_endpoint("POST /sos/trigger (new)", "POST", "/sos/trigger", sos_data)

# SOS alerts history
success &= test_endpoint("GET /sos_alerts (legacy)", "GET", "/sos_alerts")
success &= test_endpoint("GET /sos/alerts (new)", "GET", "/sos/alerts")

# Report Crime
crime_data = {
    "lat": 17.4350,
    "lng": 78.3450,
    "description": "Suspicious activity",
    "severity": 8
}
success &= test_endpoint("POST /report_crime (legacy)", "POST", "/report_crime", crime_data)

# Segment Diagnostics
success &= test_endpoint("GET /segment/1", "GET", "/segment/1")

print(f"All basic endpoints test passed: {success}")
