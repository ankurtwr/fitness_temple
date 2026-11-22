"""
Unit & integration tests for authentication and session management.
"""

from app.config import settings
from app.dependencies import reset_login_attempts


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Fitness Temple" in response.text
    assert 'name="username"' in response.text


def test_login_success(client):
    reset_login_attempts("admin")
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["Location"] == "/"
    assert "session" in client.cookies


def test_login_invalid_password(client):
    reset_login_attempts("admin")
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_login_rate_limiting(client):
    reset_login_attempts("admin")
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        res = client.post(
            "/login",
            data={"username": "admin", "password": "badpassword"},
            follow_redirects=False,
        )
        assert res.status_code == 401

    # Next attempt should be locked out (HTTP 429)
    locked_res = client.post(
        "/login",
        data={"username": "admin", "password": "badpassword"},
        follow_redirects=False,
    )
    assert locked_res.status_code == 429
    assert "Account locked" in locked_res.text
    reset_login_attempts("admin")


def test_logout(auth_client):
    res = auth_client.post("/logout", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["Location"] == "/login"
