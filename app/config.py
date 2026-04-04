import os

SECRET_KEY = os.getenv("PPP_SECRET_KEY", "ppp-secret-key-change-in-production-9f8a7b6c5d4e3f2a1b")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

DATABASE_URL = "sqlite:///./ppp.db"

# Alert thresholds (configurable via environment variables)
COST_VARIANCE_THRESHOLD = float(os.getenv("COST_VARIANCE_THRESHOLD", "0.15"))
EFFORT_VARIANCE_THRESHOLD = float(os.getenv("EFFORT_VARIANCE_THRESHOLD", "0.15"))
RISK_SCORE_THRESHOLD = float(os.getenv("RISK_SCORE_THRESHOLD", "0.8"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
LOG_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
