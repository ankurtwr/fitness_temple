"""
Authentication routes: login page, POST /login, POST /logout.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import bcrypt
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    create_session_cookie, clear_session_cookie, get_session,
    check_login_lockout, record_failed_login, reset_login_attempts,
    generate_csrf_token,
)
from app.models import Admin

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Show login form. Redirect to home if already logged in."""
    from app.main import templates
    if get_session(request):
        return RedirectResponse(url="/", status_code=303)
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "csrf_token": csrf_token,
            "error": None,
        },
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    """Validate credentials, set session cookie, redirect to home."""
    from app.main import templates
    error_ctx = {"csrf_token": "", "error": None}

    # Check lockout
    try:
        check_login_lockout(username)
    except Exception as e:
        error_ctx["error"] = str(e.detail) if hasattr(e, "detail") else str(e)
        error_ctx["csrf_token"] = generate_csrf_token(request)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=error_ctx,
            status_code=429,
        )

    # Find admin
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
        record_failed_login(username)
        error_ctx["error"] = "Invalid username or password"
        error_ctx["csrf_token"] = generate_csrf_token(request)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=error_ctx,
            status_code=401,
        )

    # Success
    reset_login_attempts(username)
    response = RedirectResponse(url="/", status_code=303)
    create_session_cookie(response, admin.id, admin.username)
    return response


@router.post("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response


# ── JSON API endpoints for mobile app ──

from fastapi.responses import JSONResponse  # noqa: E402


@router.post("/api/login")
def api_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """JSON login for mobile app. Returns session token in response body."""
    try:
        check_login_lockout(username)
    except Exception as e:
        detail = str(e.detail) if hasattr(e, "detail") else str(e)
        return JSONResponse(status_code=429, content={"error": detail})

    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
        record_failed_login(username)
        return JSONResponse(status_code=401, content={"error": "Invalid username or password"})

    reset_login_attempts(username)
    from app.dependencies import _serializer, create_session_cookie, clear_session_cookie
    token = _serializer.dumps({"admin_id": admin.id, "username": admin.username})
    resp = JSONResponse(content={"token": token, "username": admin.username})
    create_session_cookie(resp, admin.id, admin.username)
    return resp


@router.post("/api/logout")
def api_logout():
    """JSON logout — clears session cookie and confirms."""
    from app.dependencies import clear_session_cookie
    resp = JSONResponse(content={"success": True})
    clear_session_cookie(resp)
    return resp
