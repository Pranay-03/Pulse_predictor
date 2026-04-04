import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Alert
from app.config import COST_VARIANCE_THRESHOLD, EFFORT_VARIANCE_THRESHOLD, RISK_SCORE_THRESHOLD
from app.services.ai_service import generate_suggestions, serialize_suggestions
from app.services.log_service import log_action


def evaluate_and_create_alert(db: Session, project, prediction_result: dict):
    """Evaluate prediction results against thresholds and create alerts if needed."""
    features = prediction_result.get("features", {})
    risk_score = prediction_result.get("risk_score", 0)
    risk_label = prediction_result.get("risk", "Safe")

    cv = features.get("cost_variance", 0)
    ev = features.get("effort_variance", 0)

    alerts_created = []

    # Check cost variance threshold
    if cv > COST_VARIANCE_THRESHOLD:
        alert = _create_alert(
            db=db,
            project=project,
            alert_type="COST_OVERRUN",
            severity=_determine_severity(cv),
            risk_score=risk_score,
            message=f"Cost variance of {cv:.1%} exceeds threshold of {COST_VARIANCE_THRESHOLD:.1%}",
            features=features,
            tech_stack=project.tech_stack,
        )
        alerts_created.append(alert)

    # Check effort variance threshold
    if ev > EFFORT_VARIANCE_THRESHOLD:
        alert = _create_alert(
            db=db,
            project=project,
            alert_type="EFFORT_OVERRUN",
            severity=_determine_severity(ev),
            risk_score=risk_score,
            message=f"Effort variance of {ev:.1%} exceeds threshold of {EFFORT_VARIANCE_THRESHOLD:.1%}",
            features=features,
            tech_stack=project.tech_stack,
        )
        alerts_created.append(alert)

    # Check risk score threshold
    if risk_score > RISK_SCORE_THRESHOLD:
        alert = _create_alert(
            db=db,
            project=project,
            alert_type="HIGH_RISK",
            severity="High Risk",
            risk_score=risk_score,
            message=f"Risk score of {risk_score:.2f} exceeds threshold of {RISK_SCORE_THRESHOLD}. Predicted risk: {risk_label}",
            features=features,
            tech_stack=project.tech_stack,
        )
        alerts_created.append(alert)

    if alerts_created:
        log_action(
            db,
            project.manager_id,
            "SYSTEM",
            "ALERT_GENERATED",
            f"/projects/{project.id}",
            {"alert_count": len(alerts_created), "project_id": project.id},
        )

    return alerts_created


def _create_alert(db, project, alert_type, severity, risk_score, message, features, tech_stack):
    """Create a single alert with AI suggestions."""
    metrics = {**features, "risk_score": risk_score, "tech_stack": tech_stack}
    suggestions = generate_suggestions(metrics)

    alert = Alert(
        project_id=project.id,
        manager_id=project.manager_id,
        alert_type=alert_type,
        severity=severity,
        risk_score=risk_score,
        message=message,
        ai_suggestions=serialize_suggestions(suggestions),
        status="UNREAD",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def _determine_severity(variance: float) -> str:
    """Determine alert severity based on variance magnitude."""
    if variance > 0.3:
        return "High Risk"
    elif variance > 0.15:
        return "Warning"
    return "Safe"


def mark_alert_seen(db: Session, alert_id: int, user_id: int) -> Alert:
    """Mark an alert as SEEN."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        return None
    if alert.status == "UNREAD":
        alert.status = "SEEN"
        db.commit()
    return alert


def mark_alert_acknowledged(db: Session, alert_id: int, user_id: int) -> Alert:
    """Mark an alert as ACKNOWLEDGED."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        return None
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    return alert
