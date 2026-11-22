"""
Shared dependencies for FastAPI endpoints:
- Session management (signed cookies via itsdangerous)
- CSRF protection (HMAC-based double-submit)
- Auth guards for pages vs API routes
- Device key hashing (SHA-256, fast enough for /scan's <200ms target)
"""

import hashlib
import hmac as hmac_mod
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.responses import Response

from app.config import settings

# ── Session cookie serializer ──
_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def create_session_cookie(response: Response, admin_id: int, username: str) -> None:
    """Set a signed, HttpOnly session cookie."""
    token = _serializer.dumps({"admin_id": admin_id, "username": username})
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE,
        secure=False,  # set True behind HTTPS/Nginx
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie("session")


def get_session(request: Request) -> dict | None:
    """Return session payload or None if invalid/missing."""
    cookie = request.cookies.get("session")
    if not cookie:
        return None
    try:
        return _serializer.loads(cookie, max_age=settings.SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


# ── Auth dependencies ──

def require_admin_api(request: Request) -> dict:
    """For JSON API routes — returns 401 on failure.
    Accepts both session cookie (web) and Bearer token (mobile app).
    """
    # 1. Try session cookie first (web UI path)
    session = get_session(request)
    if session:
        return session

    # 2. Try Authorization: Bearer <token> header (mobile app path)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = _serializer.loads(token, max_age=settings.SESSION_MAX_AGE)
            return payload
        except (BadSignature, SignatureExpired):
            pass

    raise HTTPException(status_code=401, detail="Not authenticated")


def require_admin_page(request: Request):
    """For HTML page routes — redirects to /login on failure."""
    session = get_session(request)
    if not session:
        raise HTTPException(
            status_code=303,
            headers={"Location": "/login"},
        )
    return session


# ── CSRF protection ──

def generate_csrf_token(request: Request) -> str:
    """
    Deterministic CSRF token derived from session cookie via HMAC.
    No server-side storage needed — the session cookie IS the secret.
    """
    cookie = request.cookies.get("session", "")
    return hmac_mod.new(
        settings.SECRET_KEY.encode(), cookie.encode(), hashlib.sha256
    ).hexdigest()[:32]


def verify_csrf_token(request: Request, token: str) -> None:
    """Compare submitted token against expected. Raises 403 on mismatch.
    Bearer token requests (from mobile app/APIs) are inherently immune to CSRF.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return

    expected = generate_csrf_token(request)
    if not hmac_mod.compare_digest(expected, token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


# ── Device key hashing (SHA-256, not bcrypt) ──
# bcrypt takes ~100ms which would blow the /scan <200ms budget.
# SHA-256 is fine for machine API keys (long, random strings).

def hash_device_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def verify_device_key(key: str, key_hash: str) -> bool:
    return hmac_mod.compare_digest(
        hashlib.sha256(key.encode()).hexdigest(), key_hash
    )


# ── Login rate limiting (in-memory, per-worker) ──
# For a single-admin gym this is fine. For multi-worker production,
# move to Redis or a DB counter.

_login_attempts: dict = defaultdict(lambda: {"count": 0, "locked_until": 0.0})
_lock = Lock()


def check_login_lockout(username: str) -> None:
    """Raise 429 if account is locked."""
    with _lock:
        record = _login_attempts[username]
        if record["locked_until"] > time.time():
            remaining = int(record["locked_until"] - time.time())
            raise HTTPException(
                status_code=429,
                detail=f"Account locked. Try again in {remaining} seconds.",
            )


def record_failed_login(username: str) -> None:
    with _lock:
        record = _login_attempts[username]
        record["count"] += 1
        if record["count"] >= settings.LOGIN_MAX_ATTEMPTS:
            record["locked_until"] = time.time() + settings.LOGIN_LOCKOUT_SECONDS
            record["count"] = 0


def reset_login_attempts(username: str) -> None:
    with _lock:
        _login_attempts.pop(username, None)
