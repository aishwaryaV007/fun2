import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SOS_DB_PATH = BASE_DIR / "data" / "sos_alerts.db"

# CORS
CORS_ALLOWED_ORIGINS = ["*"]
CORS_ALLOWED_ORIGIN_REGEX = ".*"

# DATABASE
DATABASE_URL = "sqlite:///./safe_routes.db"