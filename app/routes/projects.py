import io
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import pandas as pd

from app.database import get_db
from app.models import Project, Prediction, Alert, User
from app.auth import get_current_user
from app.services.project_service import verify_project_ownership, validate_project_data
from app.services.ml_service import predict
from app.services.alert_service import evaluate_and_create_alert
from app.services.log_service import log_action
from app.templating import render

router = APIRouter(tags=["projects"])


@router.get("/projects", response_class=HTMLResponse)
async def list_projects(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "ADMIN":
        projects = db.query(Project).all()
    elif user.role == "MANAGER":
        projects = db.query(Project).filter(Project.manager_id == user.id).all()
    else:
        projects = db.query(Project).all()

    # Build manager lookup
    manager_ids = set(p.manager_id for p in projects)
    managers_map = {}
    if manager_ids:
        mgr_users = db.query(User).filter(User.id.in_(manager_ids)).all()
        managers_map = {u.id: u.name for u in mgr_users}

    project_data = []
    for p in projects:
        pred = (
            db.query(Prediction)
            .filter(Prediction.project_id == p.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        project_data.append({
            "project": p,
            "prediction": pred,
            "manager_name": managers_map.get(p.manager_id, "Unassigned"),
        })

    msg = request.query_params.get("msg", "")
    error = request.query_params.get("error", "")

    # ── Chart data ──
    import json as _json

    # Risk distribution (pie chart)
    risk_counts = {"Safe": 0, "Warning": 0, "High Risk": 0}
    # Status distribution (pie chart)
    status_counts = {}
    # Per-project overrun bar chart (top 10 by overrun)
    overrun_items = []
    # Cost: planned vs actual (bar chart, non-VIEWER only)
    cost_labels = []
    cost_planned = []
    cost_actual = []
    # Manager workload (bar chart, ADMIN only)
    manager_project_counts = {}

    for item in project_data:
        p = item["project"]
        pred = item["prediction"]
        mgr_name = item["manager_name"]

        # Risk
        if pred and pred.predicted_risk in risk_counts:
            risk_counts[pred.predicted_risk] += 1

        # Status
        st = p.status or "Unknown"
        status_counts[st] = status_counts.get(st, 0) + 1

        # Overrun
        if pred:
            overrun_items.append({"name": p.name[:20], "overrun": round(pred.predicted_overrun, 1)})

        # Cost (top 15 by planned cost)
        cost_labels.append(p.name[:18])
        cost_planned.append(round(p.planned_cost or 0, 0))
        cost_actual.append(round(p.actual_cost or 0, 0))

        # Manager workload
        manager_project_counts[mgr_name] = manager_project_counts.get(mgr_name, 0) + 1

    # Sort overrun descending, take top 10
    overrun_items.sort(key=lambda x: x["overrun"], reverse=True)
    overrun_top = overrun_items[:10]

    # Sort cost by planned descending, take top 12
    cost_sorted = sorted(zip(cost_labels, cost_planned, cost_actual), key=lambda x: x[1], reverse=True)[:12]
    if cost_sorted:
        cost_labels, cost_planned, cost_actual = zip(*cost_sorted)
    else:
        cost_labels, cost_planned, cost_actual = [], [], []

    chart_data = {
        "risk_labels": list(risk_counts.keys()),
        "risk_values": list(risk_counts.values()),
        "status_labels": list(status_counts.keys()),
        "status_values": list(status_counts.values()),
        "overrun_labels": [o["name"] for o in overrun_top],
        "overrun_values": [o["overrun"] for o in overrun_top],
        "cost_labels": list(cost_labels),
        "cost_planned": list(cost_planned),
        "cost_actual": list(cost_actual),
        "manager_labels": list(manager_project_counts.keys()),
        "manager_values": list(manager_project_counts.values()),
    }

    return render("dashboard.html", request, {
        "user": user,
        "project_data": project_data,
        "chart_data_json": _json.dumps(chart_data),
        "msg": msg,
        "error": error,
    })


@router.get("/projects/create", response_class=HTMLResponse)
async def create_project_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if user.role not in ("ADMIN", "MANAGER"):
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)
    managers = db.query(User).filter(User.role.in_(["ADMIN", "MANAGER"])).all() if user.role == "ADMIN" else []
    return render("create_project.html", request, {"user": user, "managers": managers})


@router.post("/projects/create")
async def create_project(
    request: Request,
    name: str = Form(...),
    planned_cost: float = Form(0),
    actual_cost: float = Form(0),
    planned_effort: float = Form(0),
    actual_effort: float = Form(0),
    resource_count: int = Form(1),
    start_date: str = Form(""),
    end_date: str = Form(""),
    tech_stack: str = Form(""),
    status: str = Form("Active"),
    manager_id: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "MANAGER"):
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)

    # Determine manager: ADMIN can assign, others default to self
    assigned_manager_id = user.id
    if user.role == "ADMIN" and manager_id > 0:
        assigned_manager_id = manager_id

    data = {
        "name": name,
        "planned_cost": planned_cost,
        "actual_cost": actual_cost,
        "planned_effort": planned_effort,
        "actual_effort": actual_effort,
        "resource_count": resource_count,
    }
    errors = validate_project_data(data)
    if errors:
        managers = db.query(User).filter(User.role.in_(["ADMIN", "MANAGER"])).all() if user.role == "ADMIN" else []
        return render("create_project.html", request, {"user": user, "managers": managers, "error": "; ".join(errors)})

    project = Project(
        name=name,
        manager_id=assigned_manager_id,
        planned_cost=planned_cost,
        actual_cost=actual_cost,
        planned_effort=planned_effort,
        actual_effort=actual_effort,
        resource_count=resource_count,
        start_date=start_date,
        end_date=end_date,
        tech_stack=tech_stack,
        status=status,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Run prediction pipeline
    prediction_result = predict(project)
    pred = Prediction(
        project_id=project.id,
        predicted_risk=prediction_result["risk"],
        predicted_overrun=prediction_result["overrun_pct"],
    )
    db.add(pred)
    db.commit()

    # Evaluate alerts
    evaluate_and_create_alert(db, project, prediction_result)

    log_action(
        db,
        user.id,
        user.role,
        "CREATE_PROJECT",
        "/projects/create",
        {"project_id": project.id, "project_name": name},
    )

    return RedirectResponse(url="/projects?msg=Project+created+successfully", status_code=303)


@router.get("/projects/upload", response_class=HTMLResponse)
async def upload_page(request: Request, user: User = Depends(get_current_user)):
    if user.role not in ("ADMIN", "MANAGER"):
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)
    return render("upload.html", request, {"user": user})


@router.post("/projects/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "MANAGER"):
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)

    if not file.filename.endswith(".csv"):
        return render("upload.html", request, {"user": user, "error": "Please upload a CSV file"})

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        return render("upload.html", request, {"user": user, "error": f"Error reading CSV: {str(e)}"})

    required_fields = ["name", "planned_cost", "actual_cost", "planned_effort", "actual_effort"]
    missing = [f for f in required_fields if f not in df.columns]
    if missing:
        return render("upload.html", request, {
            "user": user,
            "error": f"Missing required columns: {', '.join(missing)}",
        })

    created = 0
    errors_list = []

    for idx, row in df.iterrows():
        try:
            for field in ["planned_cost", "actual_cost", "planned_effort", "actual_effort"]:
                val = row.get(field)
                if pd.notna(val) and float(val) < 0:
                    errors_list.append(f"Row {idx + 1}: {field} cannot be negative")
                    break
            else:
                def safe_str(val, default=""):
                    if pd.isna(val):
                        return default
                    return str(val)

                # Resolve manager_id from CSV or default to uploader
                csv_manager_id = user.id
                if "manager_id" in row.index and pd.notna(row.get("manager_id")):
                    candidate = int(row["manager_id"])
                    mgr = db.query(User).filter(User.id == candidate, User.role.in_(["ADMIN", "MANAGER"])).first()
                    if mgr:
                        csv_manager_id = mgr.id

                project = Project(
                    name=str(row["name"]),
                    manager_id=csv_manager_id,
                    planned_cost=float(row.get("planned_cost", 0) or 0),
                    actual_cost=float(row.get("actual_cost", 0) or 0),
                    planned_effort=float(row.get("planned_effort", 0) or 0),
                    actual_effort=float(row.get("actual_effort", 0) or 0),
                    resource_count=int(row.get("resource_count", 1) if pd.notna(row.get("resource_count")) else 1),
                    start_date=safe_str(row.get("start_date")),
                    end_date=safe_str(row.get("end_date")),
                    tech_stack=safe_str(row.get("tech_stack")),
                    status=safe_str(row.get("status"), "Active"),
                )
                db.add(project)
                db.commit()
                db.refresh(project)

                prediction_result = predict(project)
                pred = Prediction(
                    project_id=project.id,
                    predicted_risk=prediction_result["risk"],
                    predicted_overrun=prediction_result["overrun_pct"],
                )
                db.add(pred)
                db.commit()

                evaluate_and_create_alert(db, project, prediction_result)
                created += 1
        except Exception as e:
            db.rollback()
            errors_list.append(f"Row {idx + 1}: {str(e)}")

    log_action(
        db,
        user.id,
        user.role,
        "UPLOAD_CSV",
        "/projects/upload",
        {"projects_created": created, "errors": len(errors_list)},
    )

    msg = f"Successfully imported {created} projects"
    if errors_list:
        msg += f" with {len(errors_list)} errors"
    return RedirectResponse(url=f"/projects?msg={msg.replace(' ', '+')}", status_code=303)


@router.get("/projects/edit/{project_id}", response_class=HTMLResponse)
async def edit_project_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "VIEWER":
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)
    project = verify_project_ownership(db, project_id, user)
    managers = db.query(User).filter(User.role.in_(["ADMIN", "MANAGER"])).all() if user.role == "ADMIN" else []
    return render("edit_project.html", request, {"user": user, "project": project, "managers": managers})


@router.post("/projects/edit/{project_id}")
async def edit_project(
    project_id: int,
    request: Request,
    name: str = Form(...),
    planned_cost: float = Form(0),
    actual_cost: float = Form(0),
    planned_effort: float = Form(0),
    actual_effort: float = Form(0),
    resource_count: int = Form(1),
    start_date: str = Form(""),
    end_date: str = Form(""),
    tech_stack: str = Form(""),
    status: str = Form("Active"),
    manager_id: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "VIEWER":
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)

    project = verify_project_ownership(db, project_id, user)

    data = {
        "name": name,
        "planned_cost": planned_cost,
        "actual_cost": actual_cost,
        "planned_effort": planned_effort,
        "actual_effort": actual_effort,
        "resource_count": resource_count,
    }
    errors = validate_project_data(data)
    if errors:
        managers = db.query(User).filter(User.role.in_(["ADMIN", "MANAGER"])).all() if user.role == "ADMIN" else []
        return render("edit_project.html", request, {"user": user, "project": project, "managers": managers, "error": "; ".join(errors)})

    # ADMIN can reassign manager
    if user.role == "ADMIN" and manager_id > 0:
        project.manager_id = manager_id

    project.name = name
    project.planned_cost = planned_cost
    project.actual_cost = actual_cost
    project.planned_effort = planned_effort
    project.actual_effort = actual_effort
    project.resource_count = resource_count
    project.start_date = start_date
    project.end_date = end_date
    project.tech_stack = tech_stack
    project.status = status
    db.commit()
    db.refresh(project)

    # Re-run prediction pipeline
    prediction_result = predict(project)
    pred = Prediction(
        project_id=project.id,
        predicted_risk=prediction_result["risk"],
        predicted_overrun=prediction_result["overrun_pct"],
    )
    db.add(pred)
    db.commit()

    evaluate_and_create_alert(db, project, prediction_result)

    log_action(
        db,
        user.id,
        user.role,
        "UPDATE_PROJECT",
        f"/projects/edit/{project_id}",
        {"project_id": project.id},
    )

    return RedirectResponse(url="/projects?msg=Project+updated+successfully", status_code=303)


@router.post("/projects/delete/{project_id}")
async def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "MANAGER"):
        return RedirectResponse(url="/projects?error=Permission+denied", status_code=303)

    project = verify_project_ownership(db, project_id, user)

    # Delete related records
    db.query(Prediction).filter(Prediction.project_id == project_id).delete()
    db.query(Alert).filter(Alert.project_id == project_id).delete()
    db.delete(project)
    db.commit()

    log_action(
        db,
        user.id,
        user.role,
        "DELETE_PROJECT",
        f"/projects/delete/{project_id}",
        {"project_id": project_id, "project_name": project.name},
    )

    return RedirectResponse(url="/projects?msg=Project+deleted", status_code=303)


# ── API Ingestion Endpoint ──
@router.post("/api/projects/ingest")
async def api_ingest(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """API endpoint for JSON-based project ingestion."""
    if user.role not in ("ADMIN", "MANAGER"):
        return {"error": "Permission denied"}, 403

    body = await request.json()
    projects_data = body if isinstance(body, list) else [body]

    results = []
    for item in projects_data:
        errors = validate_project_data(item)
        if errors:
            results.append({"name": item.get("name", "unknown"), "status": "error", "errors": errors})
            continue

        project = Project(
            name=item["name"],
            manager_id=user.id,
            planned_cost=item.get("planned_cost", 0),
            actual_cost=item.get("actual_cost", 0),
            planned_effort=item.get("planned_effort", 0),
            actual_effort=item.get("actual_effort", 0),
            resource_count=item.get("resource_count", 1),
            start_date=item.get("start_date", ""),
            end_date=item.get("end_date", ""),
            tech_stack=item.get("tech_stack", ""),
            status=item.get("status", "Active"),
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        prediction_result = predict(project)
        pred = Prediction(
            project_id=project.id,
            predicted_risk=prediction_result["risk"],
            predicted_overrun=prediction_result["overrun_pct"],
        )
        db.add(pred)
        db.commit()

        evaluate_and_create_alert(db, project, prediction_result)
        results.append({"name": project.name, "id": project.id, "status": "created", "risk": prediction_result["risk"]})

    log_action(db, user.id, user.role, "API_INGEST", "/api/projects/ingest", {"count": len(results)})

    return {"results": results}
