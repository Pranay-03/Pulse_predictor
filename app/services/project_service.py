from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Project, User


def verify_project_ownership(db: Session, project_id: int, user: User) -> Project:
    """Verify user has access to the project. Double-validation at service layer."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if user.role == "ADMIN":
        return project

    if user.role == "MANAGER" and project.manager_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied: not your project")

    # VIEWER can read any project
    return project


def validate_project_data(data: dict) -> list:
    """Validate project data and return list of error strings."""
    errors = []

    if not data.get("name"):
        errors.append("Project name is required")

    for field in ["planned_cost", "actual_cost", "planned_effort", "actual_effort"]:
        val = data.get(field)
        if val is not None and val < 0:
            errors.append(f"{field.replace('_', ' ').title()} cannot be negative")

    rc = data.get("resource_count")
    if rc is not None and rc < 0:
        errors.append("Resource count cannot be negative")

    return errors
