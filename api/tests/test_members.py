"""
Unit & integration tests for Member management endpoints.
"""

from datetime import date, timedelta
from app.dependencies import generate_csrf_token
from app.models import Member, Membership, Card, PendingAssignment, AssignmentStatus


def _get_csrf_and_cookies(auth_client):
    """Compute CSRF token matching the session cookie in auth_client."""
    import hmac, hashlib
    from app.config import settings
    cookie = auth_client.cookies.get("session", "")
    return hmac.new(settings.SECRET_KEY.encode(), cookie.encode(), hashlib.sha256).hexdigest()[:32]


def test_create_member_success(auth_client, db_session):
    csrf = _get_csrf_and_cookies(auth_client)
    payload = {
        "name": "Kavita Singh",
        "phone": "9123456789",
        "address": "Flat 402, Green Valley Apartments",
        "plan_id": 1,
        "amount_paid": 1000.0,
        "csrf_token": csrf,
    }
    res = auth_client.post("/api/members", data=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "member_id" in data

    # Verify database
    member = db_session.query(Member).filter(Member.phone == "9123456789").first()
    assert member is not None
    assert member.name == "Kavita Singh"
    assert member.memberships.count() == 1


def test_create_member_duplicate_phone(auth_client, db_session):
    csrf = _get_csrf_and_cookies(auth_client)
    m = Member(name="Existing Person", phone="9000000001")
    db_session.add(m)
    db_session.commit()

    payload = {
        "name": "New Person",
        "phone": "9000000001",
        "plan_id": 1,
        "amount_paid": 1000.0,
        "csrf_token": csrf,
    }
    res = auth_client.post("/api/members", data=payload)
    assert res.status_code == 200
    data = res.json()
    assert "error" in data
    assert "already registered" in data["error"]


def test_search_members(auth_client, db_session):
    m1 = Member(name="Vikram Rathore", phone="9811122233")
    m2 = Member(name="Deepak Joshi", phone="9822233344")
    db_session.add_all([m1, m2])
    db_session.commit()

    # Search by name
    res1 = auth_client.get("/api/members?search=Vikram")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["members"]) == 1
    assert data1["members"][0]["name"] == "Vikram Rathore"

    # Search by phone
    res2 = auth_client.get("/api/members?search=98222")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["members"]) == 1
    assert data2["members"][0]["name"] == "Deepak Joshi"


def test_membership_renewal_date_preservation(auth_client, db_session):
    """
    If current end_date >= today: new start = current.end_date + 1 day
    If already expired: new start = today
    """
    csrf = _get_csrf_and_cookies(auth_client)

    member = Member(name="Pooja Sharma", phone="9911223344")
    db_session.add(member)
    db_session.flush()

    # Scenario A: Active member with 10 days left
    future_expiry = date.today() + timedelta(days=10)
    current_ms = Membership(
        member_id=member.id,
        plan_id=1,
        start_date=date.today() - timedelta(days=20),
        end_date=future_expiry,
        amount_paid=1000.0,
    )
    db_session.add(current_ms)
    db_session.commit()

    # Renew for 30 days (Plan 1)
    res = auth_client.post(
        f"/api/members/{member.id}/renew",
        data={"plan_id": 1, "amount_paid": 1000.0, "csrf_token": csrf},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    # Expected new end date is future_expiry + 1 day + 30 days
    expected_end = future_expiry + timedelta(days=1) + timedelta(days=30)
    assert data["end_date"] == expected_end.isoformat()


def test_report_lost_card(auth_client, db_session):
    csrf = _get_csrf_and_cookies(auth_client)

    member = Member(name="Sameer Khan", phone="9877788899")
    db_session.add(member)
    db_session.flush()

    card = Card(uid="ACTIVE999", member_id=member.id, active=True)
    db_session.add(card)
    db_session.commit()

    res = auth_client.post(
        f"/api/members/{member.id}/report-lost",
        data={"csrf_token": csrf},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Card must now be inactive
    db_session.refresh(card)
    assert card.active is False
    assert card.deactivated_at is not None
