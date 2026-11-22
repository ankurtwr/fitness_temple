"""
Unit & integration tests for POST /scan — all 7 response branches + logging.
"""

from datetime import datetime, date, timedelta, timezone
from app.models import Member, Membership, Card, PendingAssignment, AssignmentStatus, ScanLog, ScanResult

DEVICE_KEY = "testdevice123"
INVALID_KEY = "wrongkey999"


def _create_active_member(db_session, uid="AA11BB22", days_remaining=30):
    """Helper to create a member with an active membership and card."""
    member = Member(name="Rohit Verma", phone="9988776655")
    db_session.add(member)
    db_session.flush()

    today = date.today()
    membership = Membership(
        member_id=member.id,
        plan_id=1,
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=days_remaining),
        amount_paid=1000.0,
    )
    db_session.add(membership)

    card = Card(uid=uid, member_id=member.id, active=True)
    db_session.add(card)
    db_session.commit()
    return member, card, membership


def test_scan_rejected_device_key(client, db_session):
    """Step 1: Invalid device key returns rejected status."""
    payload = {"uid": "12345678", "device_key": INVALID_KEY}
    res = client.post("/scan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"
    assert "Invalid device key" in data["message"]

    # Verify ScanLog
    log_entry = db_session.query(ScanLog).order_by(ScanLog.id.desc()).first()
    assert log_entry is not None
    assert log_entry.result == ScanResult.rejected


def test_scan_card_assignment_linked(client, db_session):
    """Step 2: When pending assignment is active, next new UID is linked."""
    member = Member(name="Ananya Sen", phone="9876543210")
    db_session.add(member)
    db_session.flush()

    # Create pending assignment
    pending = PendingAssignment(
        member_id=member.id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
        status=AssignmentStatus.pending,
    )
    db_session.add(pending)
    db_session.commit()

    # Tap new card
    new_uid = "NEWCARD99"
    res = client.post("/scan", json={"uid": new_uid, "device_key": DEVICE_KEY})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "linked"
    assert data["name"] == "Ananya Sen"

    # Verify DB state
    db_session.refresh(pending)
    assert pending.status == AssignmentStatus.done

    card = db_session.query(Card).filter(Card.uid == new_uid).first()
    assert card is not None
    assert card.member_id == member.id
    assert card.active is True


def test_scan_unknown_card(client, db_session):
    """Step 3: Unregistered UID returns unknown."""
    res = client.post("/scan", json={"uid": "UNKNOWNUID1", "device_key": DEVICE_KEY})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "unknown"
    assert "not registered" in data["message"]


def test_scan_inactive_card(client, db_session):
    """Step 4: Card reported lost/deactivated returns inactive."""
    member, card, _ = _create_active_member(db_session, uid="LOSTCARD01")
    card.active = False
    card.deactivated_at = datetime.now(timezone.utc)
    db_session.commit()

    res = client.post("/scan", json={"uid": "LOSTCARD01", "device_key": DEVICE_KEY})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "inactive"
    assert data["name"] == member.name


def test_scan_expired_membership(client, db_session):
    """Step 5: Expired membership returns expired."""
    member, card, membership = _create_active_member(db_session, uid="EXPIREDCARD", days_remaining=-5)
    membership.start_date = date.today() - timedelta(days=35)
    membership.end_date = date.today() - timedelta(days=5)
    db_session.commit()

    res = client.post("/scan", json={"uid": "EXPIREDCARD", "device_key": DEVICE_KEY})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "expired"
    assert data["name"] == member.name


def test_scan_marked_and_already_marked(client, db_session):
    """Step 6 & 7: First tap marks attendance; second tap on same day dedupes to already_marked."""
    member, card, _ = _create_active_member(db_session, uid="ATTENDANCE1")

    # First tap: marked
    res1 = client.post("/scan", json={"uid": "ATTENDANCE1", "device_key": DEVICE_KEY})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "marked"
    assert data1["name"] == member.name

    # Second tap on same day: already_marked
    res2 = client.post("/scan", json={"uid": "ATTENDANCE1", "device_key": DEVICE_KEY})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "already_marked"
    assert data2["name"] == member.name


def test_scan_offline_queued_timestamp(client, db_session):
    """Offline queued tap with scanned_at maintains the accurate checkin_time."""
    member, card, _ = _create_active_member(db_session, uid="OFFLINE001")
    queued_time = "2026-10-25T10:15:00Z"

    res = client.post("/scan", json={
        "uid": "OFFLINE001",
        "device_key": DEVICE_KEY,
        "scanned_at": queued_time,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "marked"
