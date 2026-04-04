import os
import numpy as np
import joblib
from datetime import datetime
from app.config import MODEL_DIR

_classifier = None
_regressor = None


def load_models():
    """Load trained ML models from disk."""
    global _classifier, _regressor
    clf_path = os.path.join(MODEL_DIR, "risk_classifier.joblib")
    reg_path = os.path.join(MODEL_DIR, "overrun_regressor.joblib")

    if os.path.exists(clf_path):
        _classifier = joblib.load(clf_path)
    if os.path.exists(reg_path):
        _regressor = joblib.load(reg_path)


def compute_features(project) -> dict:
    """Compute engineered features from raw project data."""
    try:
        start = datetime.strptime(str(project.start_date), "%Y-%m-%d")
        end = datetime.strptime(str(project.end_date), "%Y-%m-%d")
        duration = max((end - start).days, 1)
    except (ValueError, TypeError):
        duration = 1

    planned_cost = project.planned_cost or 0
    actual_cost = project.actual_cost or 0
    planned_effort = project.planned_effort or 0
    actual_effort = project.actual_effort or 0
    resource_count = project.resource_count or 1

    cost_variance = (actual_cost - planned_cost) / max(planned_cost, 1)
    effort_variance = (actual_effort - planned_effort) / max(planned_effort, 1)
    burn_rate = actual_cost / max(duration, 1)
    resource_utilization = actual_effort / max(resource_count * duration, 1)

    return {
        "cost_variance": cost_variance,
        "effort_variance": effort_variance,
        "burn_rate": burn_rate,
        "resource_utilization": resource_utilization,
        "duration": duration,
        "resource_count": resource_count,
    }


def predict(project) -> dict:
    """Run ML prediction on a project. Returns risk label, overrun %, risk score, and features."""
    global _classifier, _regressor

    if _classifier is None or _regressor is None:
        load_models()

    features = compute_features(project)

    if _classifier is None or _regressor is None:
        # Fallback: rule-based prediction when models aren't available
        cv = features["cost_variance"]
        ev = features["effort_variance"]
        combined = cv * 0.5 + ev * 0.5
        if combined > 0.3:
            risk = "High Risk"
            risk_score = min(0.6 + combined, 1.0)
        elif combined > 0.1:
            risk = "Warning"
            risk_score = 0.3 + combined
        else:
            risk = "Safe"
            risk_score = max(0.1, combined)
        return {
            "risk": risk,
            "overrun_pct": round(cv * 100, 2),
            "risk_score": round(risk_score, 4),
            "features": features,
        }

    import pandas as pd
    feature_array = pd.DataFrame(
        [[
            features["cost_variance"],
            features["effort_variance"],
            features["burn_rate"],
            features["resource_utilization"],
            features["duration"],
            features["resource_count"],
        ]],
        columns=["cost_variance", "effort_variance", "burn_rate",
                 "resource_utilization", "duration", "resource_count"],
    )

    risk = _classifier.predict(feature_array)[0]
    risk_proba = _classifier.predict_proba(feature_array)[0]

    # Risk score = probability of High Risk class
    classes = list(_classifier.classes_)
    if "High Risk" in classes:
        risk_score = float(risk_proba[classes.index("High Risk")])
    else:
        risk_score = float(max(risk_proba))

    overrun_pct = float(_regressor.predict(feature_array)[0])

    return {
        "risk": risk,
        "overrun_pct": round(overrun_pct, 2),
        "risk_score": round(risk_score, 4),
        "features": features,
    }
