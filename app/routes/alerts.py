from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Project, User, Log
from app.auth import get_current_user
from app.services.alert_service import mark_alert_seen, mark_alert_acknowledged
from app.services.ai_service import deserialize_suggestions
from app.services.log_service import log_action
from app.templating import render

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_class=HTMLResponse)
async def list_alerts(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "ADMIN":
        alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    elif user.role == "MANAGER":
        alerts = (
            db.query(Alert)
            .filter(Alert.manager_id == user.id)
            .order_by(Alert.created_at.desc())
            .all()
        )
    else:
        alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()

    alert_data = []
    for a in alerts:
        project = db.query(Project).filter(Project.id == a.project_id).first()
        suggestions = deserialize_suggestions(a.ai_suggestions) if a.ai_suggestions else {}
        alert_data.append({
            "alert": a,
            "project_name": project.name if project else "Unknown",
            "suggestions": suggestions,
        })

    msg = request.query_params.get("msg", "")

    # ── Chart data for alerts page ──
    import json as _json
    severity_counts = {"Safe": 0, "Warning": 0, "High Risk": 0}
    status_counts = {"UNREAD": 0, "SEEN": 0, "ACKNOWLEDGED": 0}
    for item in alert_data:
        a = item["alert"]
        sev = a.severity or "Unknown"
        if sev in severity_counts:
            severity_counts[sev] += 1
        st = a.status or "UNREAD"
        if st in status_counts:
            status_counts[st] += 1

    alert_chart = {
        "severity_labels": list(severity_counts.keys()),
        "severity_values": list(severity_counts.values()),
        "status_labels": list(status_counts.keys()),
        "status_values": list(status_counts.values()),
    }

    return render("alerts.html", request, {
        "user": user,
        "alert_data": alert_data,
        "alert_chart_json": _json.dumps(alert_chart),
        "msg": msg,
    })


@router.post("/alerts/{alert_id}/seen")
async def alert_seen(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        return RedirectResponse(url="/alerts?msg=Alert+not+found", status_code=303)

    # Ownership check
    if user.role != "ADMIN" and alert.manager_id != user.id:
        return RedirectResponse(url="/alerts?msg=Permission+denied", status_code=303)

    mark_alert_seen(db, alert_id, user.id)
    log_action(db, user.id, user.role, "ALERT_SEEN", f"/alerts/{alert_id}/seen", {"alert_id": alert_id})

    return RedirectResponse(url="/alerts?msg=Alert+marked+as+seen", status_code=303)


@router.post("/alerts/{alert_id}/acknowledge")
async def alert_acknowledge(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        return RedirectResponse(url="/alerts?msg=Alert+not+found", status_code=303)

    if user.role != "ADMIN" and alert.manager_id != user.id:
        return RedirectResponse(url="/alerts?msg=Permission+denied", status_code=303)

    mark_alert_acknowledged(db, alert_id, user.id)
    log_action(
        db,
        user.id,
        user.role,
        "ALERT_ACKNOWLEDGED",
        f"/alerts/{alert_id}/acknowledge",
        {"alert_id": alert_id},
    )

    return RedirectResponse(url="/alerts?msg=Alert+acknowledged", status_code=303)


# ── Admin Panel ──
@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "ADMIN":
        return RedirectResponse(url="/projects?error=Admin+access+required", status_code=303)

    # All alerts
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    alert_data = []
    for a in alerts:
        project = db.query(Project).filter(Project.id == a.project_id).first()
        manager = db.query(User).filter(User.id == a.manager_id).first()
        suggestions = deserialize_suggestions(a.ai_suggestions) if a.ai_suggestions else {}
        alert_data.append({
            "alert": a,
            "project_name": project.name if project else "Unknown",
            "manager_name": manager.name if manager else "Unknown",
            "suggestions": suggestions,
        })

    # Recent logs
    recent_logs = db.query(Log).order_by(Log.timestamp.desc()).limit(50).all()

    # Stats
    total_projects = db.query(Project).count()
    total_alerts = db.query(Alert).count()
    unread_alerts = db.query(Alert).filter(Alert.status == "UNREAD").count()
    total_users = db.query(User).count()

    msg = request.query_params.get("msg", "")

    return render("admin.html", request, {
        "user": user,
        "alert_data": alert_data,
        "recent_logs": recent_logs,
        "stats": {
            "total_projects": total_projects,
            "total_alerts": total_alerts,
            "unread_alerts": unread_alerts,
            "total_users": total_users,
        },
        "msg": msg,
    })
