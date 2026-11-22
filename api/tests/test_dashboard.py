"""
Unit & integration tests for Live Dashboard and Attendance Polling.
"""

from datetime import datetime, date, timedelta, timezone
from app.models import Member, Membership, Card, Attendance


def test_dashboard_page_requires_auth(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_dashboard_page_loads_for_admin(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert "Live Attendance" in response.text
    assert "attendance-tbody" in response.text


def test_attendance_today_polling_api(auth_client, db_session):
    today = date.today()
    member = Member(name="Karan Johar", phone="9988112233")
    db_session.add(member)
    db_session.flush()

    membership = Membership(
        member_id=member.id,
        plan_id=1,
        start_date=today,
        end_date=today + timedelta(days=30),
        amount_paid=1000.0,
    )
    db_session.add(membership)

    att = Attendance(
        member_id=member.id,
        attendance_date=today,
        checkin_time=datetime.now(timezone.utc),
    )
    db_session.add(att)
    db_session.commit()

    # Poll with since_id=0
    res = auth_client.get("/api/attendance/today?since_id=0")
    assert res.status_code == 200
    data = res.json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["name"] == "Karan Johar"
    assert data["rows"][0]["is_expired"] is False

    # Poll with since_id matching the row -> should return empty rows
    res2 = auth_client.get(f"/api/attendance/today?since_id={att.id}")
    assert res2.status_code == 200
    assert len(res2.json()["rows"]) == 0
