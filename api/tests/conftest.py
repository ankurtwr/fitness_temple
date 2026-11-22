"""
Pytest fixtures and configuration for Fitness Temple test suite.
Uses an in-memory SQLite database and FastAPI TestClient.
"""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-1234567890abcdef")

from datetime import datetime, date, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import bcrypt

from app.database import Base, get_db
from app.main import app
from app.models import Admin, Device, Plan, Member, Membership, Card
from app.dependencies import hash_device_key, create_session_cookie

# SQLite in-memory database for rapid, isolated testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh tables for every test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Seed baseline plans
    plans = [
        Plan(id=1, name="1 Month", duration_days=30, price=1000, active=True),
        Plan(id=2, name="3 Months", duration_days=90, price=2500, active=True),
        Plan(id=3, name="6 Months", duration_days=180, price=4500, active=True),
        Plan(id=4, name="12 Months", duration_days=365, price=8000, active=True),
    ]
    for p in plans:
        session.add(p)

    # Seed admin user (admin / admin123)
    admin = Admin(
        username="admin",
        password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8"),
    )
    session.add(admin)

    # Seed test device (key: testdevice123)
    device = Device(
        name="entrance-reader-1",
        secret_key_hash=hash_device_key("testdevice123"),
    )
    session.add(device)

    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Test client with db dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client, db_session):
    """Test client with an active admin session cookie."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "session" in client.cookies
    return client

