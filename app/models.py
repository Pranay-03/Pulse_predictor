from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('ADMIN', 'MANAGER', 'VIEWER')", name="check_user_role"),
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    planned_cost = Column(Float)
    actual_cost = Column(Float)
    planned_effort = Column(Float)
    actual_effort = Column(Float)
    resource_count = Column(Integer)
    start_date = Column(String)
    end_date = Column(String)
    tech_stack = Column(String)
    status = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_type = Column(String)
    severity = Column(String)
    risk_score = Column(Float)
    message = Column(Text)
    ai_suggestions = Column(Text)
    status = Column(String, default="UNREAD")
    created_at = Column(DateTime, server_default=func.now())
    acknowledged_at = Column(DateTime)

    __table_args__ = (
        CheckConstraint("status IN ('UNREAD', 'SEEN', 'ACKNOWLEDGED')", name="check_alert_status"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    predicted_risk = Column(String)
    predicted_overrun = Column(Float)
    actual_overrun = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class Log(Base):
    __tablename__ = "logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    role = Column(String)
    action = Column(String)
    endpoint = Column(String)
    metadata_ = Column("metadata", Text)
    timestamp = Column(DateTime, server_default=func.now())
