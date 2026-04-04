import logging
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Log
from app.config import LOG_DIR

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# File logger setup
logger = logging.getLogger("ppp")
logger.setLevel(logging.INFO)
_handler = logging.FileHandler(os.path.join(LOG_DIR, "ppp.log"))
_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)


def log_action(db: Session, user_id: int, role: str, action: str, endpoint: str, metadata: dict = None):
    """Log an action to both the database and log file."""
    # Database log
    log_entry = Log(
        user_id=user_id,
        role=role,
        action=action,
        endpoint=endpoint,
        metadata_=json.dumps(metadata) if metadata else None,
    )
    db.add(log_entry)
    db.commit()

    # File log
    logger.info(
        json.dumps(
            {
                "user_id": user_id,
                "role": role,
                "action": action,
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata,
            }
        )
    )
