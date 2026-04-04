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
    return _templates.TemplateResponse(name=name, request=request, context=ctx)
