from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, get_current_user_optional
from app.services.log_service import log_action
from app.templating import render

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/projects", status_code=303)
    msg = request.query_params.get("msg", "")
    return render("login.html", request, {"msg": msg})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return render("login.html", request, {"error": "Invalid email or password"})

    token = create_access_token({"user_id": user.id, "role": user.role})
    response = RedirectResponse(url="/projects", status_code=303)
    response.set_cookie(
        key="access_token", value=token, httponly=True, max_age=86400, samesite="lax"
    )

    log_action(db, user.id, user.role, "LOGIN", "/login")
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render("register.html", request)


@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("VIEWER"),
    db: Session = Depends(get_db),
):
    if len(password) < 6:
        return render("register.html", request, {"error": "Password must be at least 6 characters"})

    if role not in ("ADMIN", "MANAGER", "VIEWER"):
        return render("register.html", request, {"error": "Invalid role selected"})

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return render("register.html", request, {"error": "Email already registered"})

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, user.id, user.role, "REGISTER", "/register")

    return RedirectResponse(url="/login?msg=Registration+successful.+Please+log+in.", status_code=303)


@router.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        log_action(db, user.id, user.role, "LOGOUT", "/logout")

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
