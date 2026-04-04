# Project Pulse Predictor (PPP)

An AI-powered web application that predicts project cost/effort overruns, classifies risk, generates intelligent recommendations, and tracks alerts with lifecycle management.

## Features

- **ML-Powered Predictions**: RandomForest models for risk classification (Safe/Warning/High Risk) and cost overrun regression
- **AI Recommendation Engine**: Rule-based analysis generating root cause analysis, cost optimization, resource allocation, tech improvements, and risk mitigation plans
- **Alert System**: Configurable threshold-based alerting with lifecycle tracking (UNREAD → SEEN → ACKNOWLEDGED)
- **Role-Based Access Control**: ADMIN (full access), MANAGER (own projects), VIEWER (read-only, no financial data)
- **Data Ingestion**: CSV upload via UI and JSON API endpoint
- **Audit Logging**: Database + file logging of all user actions

## Tech Stack

| Layer     | Technology              |
|-----------|------------------------|
| Backend   | FastAPI + SQLAlchemy   |
| Database  | SQLite                 |
| Frontend  | Jinja2 + Bootstrap 5   |
| ML        | Scikit-learn           |
| Auth      | JWT (HTTP-only cookies)|

## Project Structure

```
app/
  main.py              # FastAPI app entry point
  config.py            # Configuration & thresholds
  database.py          # SQLAlchemy engine & session
  models.py            # ORM models (User, Project, Alert, Prediction, Log)
  schemas.py           # Pydantic validation schemas
  auth.py              # JWT auth, password hashing, RBAC dependencies
  templating.py        # Shared Jinja2 templates instance
  routes/
    auth.py            # Login, Register, Logout
    projects.py        # CRUD, CSV upload, API ingestion
    alerts.py          # Alert management, Admin panel
  services/
    ml_service.py      # ML model loading & prediction
    alert_service.py   # Alert evaluation & creation
    ai_service.py      # AI suggestion generation
    log_service.py     # Audit logging (DB + file)
    project_service.py # Ownership validation
  templates/           # Jinja2 HTML templates
  static/              # Static assets
data/
  sample_data.csv      # Sample project data for CSV upload testing
models/                # Trained ML models (joblib)
logs/                  # Application log files
train_model.py         # ML model training script
requirements.txt
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Train ML Models

```bash
python train_model.py
```

This generates synthetic training data and saves trained models to the `models/` directory.

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the Application

Open your browser to: **http://localhost:8000**

1. Register a new account (choose ADMIN role for full access)
2. Log in
3. Create projects or upload the sample CSV from `data/sample_data.csv`
4. View predictions and alerts on the dashboard

## Default Roles

| Role    | Permissions                                           |
|---------|------------------------------------------------------|
| ADMIN   | Full CRUD on all entities, view all alerts, admin panel |
| MANAGER | CRUD on own projects only, view own alerts            |
| VIEWER  | Read-only access, no financial fields visible         |

## Configuration

Environment variables (optional):

| Variable                  | Default | Description                          |
|---------------------------|---------|--------------------------------------|
| PPP_SECRET_KEY            | (set)   | JWT signing key                      |
| COST_VARIANCE_THRESHOLD   | 0.15    | Cost variance alert threshold (15%)  |
| EFFORT_VARIANCE_THRESHOLD | 0.15    | Effort variance alert threshold (15%)|
| RISK_SCORE_THRESHOLD      | 0.8     | Risk score alert threshold           |

## API Endpoints

### Auth
- `GET /login` - Login page
- `POST /login` - Authenticate
- `GET /register` - Registration page
- `POST /register` - Create account
- `GET /logout` - Sign out

### Projects
- `GET /projects` - Dashboard (project list)
- `GET /projects/create` - Create form
- `POST /projects/create` - Submit new project
- `GET /projects/edit/{id}` - Edit form
- `POST /projects/edit/{id}` - Update project
- `POST /projects/delete/{id}` - Delete project
- `GET /projects/upload` - CSV upload form
- `POST /projects/upload` - Process CSV upload
- `POST /api/projects/ingest` - JSON API ingestion

### Alerts
- `GET /alerts` - View alerts
- `POST /alerts/{id}/seen` - Mark as seen
- `POST /alerts/{id}/acknowledge` - Acknowledge alert
- `GET /admin` - Admin panel (ADMIN only)
