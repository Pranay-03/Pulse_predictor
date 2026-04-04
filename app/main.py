import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.auth import NotAuthenticated, InsufficientPermissions
from app.routes import auth, projects, alerts
from app.services.ml_service import load_models
from app.config import LOG_DIR, MODEL_DIR, DATA_DIR

# Ensure directories exist
for d in [LOG_DIR, MODEL_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="Project Pulse Predictor", version="1.0.0")

# Create all database tables
Base.metadata.create_all(bind=engine)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(alerts.router)


@app.on_event("startup")
async def startup():
    """Load ML models on application startup."""
    load_models()


# ── Exception Handlers ──


@app.exception_handler(NotAuthenticated)
async def not_authenticated_handler(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(InsufficientPermissions)
async def insufficient_permissions_handler(request: Request, exc: InsufficientPermissions):
    return RedirectResponse(url="/projects?error=Insufficient+permissions", status_code=303)


# ── Root redirect ──


@app.get("/")
async def root():
    return RedirectResponse(url="/projects", status_code=303)
