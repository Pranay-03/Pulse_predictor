from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os

_templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def _currency(value):
    try:
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return "0"


_templates.env.filters["currency"] = _currency


def render(name: str, request: Request, context: dict = None):
    """Render a Jinja2 template compatible with Starlette 1.0+ API."""
    ctx = context or {}

    # Auto-detect active page from request path for navbar highlighting
    path = request.url.path
    if path.startswith("/admin"):
        ctx.setdefault("active_page", "admin")
    elif path.startswith("/alerts"):
        ctx.setdefault("active_page", "alerts")
    elif path.startswith("/projects/create"):
        ctx.setdefault("active_page", "create")
    elif path.startswith("/projects/upload"):
        ctx.setdefault("active_page", "upload")
    elif path.startswith("/projects"):
        ctx.setdefault("active_page", "dashboard")

    return _templates.TemplateResponse(name=name, request=request, context=ctx)
