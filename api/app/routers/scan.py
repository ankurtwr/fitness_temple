"""
POST /scan — the most performance-critical endpoint.

Called by ESP32 on every card tap. Target: <200ms response time.
Flow is strictly ordered (see docstring on scan_card).
"""

import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import structlog

from app.database import get_db
from app.models import (
    Device, Card, Member, Membership, Attendance, ScanLog,
    PendingAssignment, ScanResult, AssignmentStatus,
)
from app.schemas import ScanRequest, ScanResponse
from app.dependencies import hash_device_key

log = structlog.get_logger()
router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist() -> datetime:
    return datetime.now(IST)


def _log_scan(
    db: Session, uid: str | None, device_id: int | None,
    result: ScanResult, start_time: float,
    scanned_at: datetime | None = None,
) -> None:
    """Write to scan_log. Uses its own commit so it's never lost on rollback."""
    elapsed_ms = int((time.time() - start_time) * 1000)
    entry = ScanLog(
        uid=uid,
        device_id=device_id,
        result=result,
        response_ms=elapsed_ms,
        scanned_at=scanned_at or datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    log.info("scan", uid=uid, result=result.value, ms=elapsed_ms)


@router.post("/scan", response_model=ScanResponse)
def scan_card(req: ScanRequest, db: Session = Depends(get_db)):
    """
    Process an RFID card tap. Steps in order:

    1. Validate device_key → 401 + log "rejected" if wrong
    2. Check pending_assignment → link card if valid new UID
    3. Look up card by UID → "unknown" / "inactive"
    4. Check membership expiry → "expired"
    5. Insert attendance (UNIQUE constraint dedupes) → "marked" / "already_marked"
    6. Log everything to scan_log with response time
    """
    start_time = time.time()
    uid = req.uid.upper().strip()

    # ── Step 1: Validate device ──
    key_hash = hash_device_key(req.device_key)
    device = db.query(Device).filter(Device.secret_key_hash == key_hash).first()
    if not device:
        _log_scan(db, uid, None, ScanResult.rejected, start_time, req.scanned_at)
        return ScanResponse(status="rejected", message="Invalid device key")

    # Update device last_seen
    device.last_seen_at = datetime.now(timezone.utc)

    # ── Step 2: Check pending card assignment ──
    now_utc = datetime.utcnow()
    pending = (
        db.query(PendingAssignment)
        .filter(
            PendingAssignment.status == AssignmentStatus.pending,
            PendingAssignment.expires_at > now_utc,
        )
        .order_by(PendingAssignment.id.desc())
        .first()
    )

    if pending:
        # Only link if this UID isn't already in the cards table
        existing_card = db.query(Card).filter(Card.uid == uid).first()
        if not existing_card:
            new_card = Card(uid=uid, member_id=pending.member_id, active=True)
            db.add(new_card)
            pending.status = AssignmentStatus.done
            db.commit()

            member = db.query(Member).filter(Member.id == pending.member_id).first()
            _log_scan(db, uid, device.id, ScanResult.linked, start_time, req.scanned_at)
            return ScanResponse(
                status="linked",
                name=member.name if member else None,
                message="Card assigned successfully",
            )
        # If UID already exists, fall through to normal processing.
        # The pending assignment stays active for the next new card tap.

    # ── Step 3: Look up card ──
    card = db.query(Card).filter(Card.uid == uid).first()
    if not card:
        _log_scan(db, uid, device.id, ScanResult.unknown, start_time, req.scanned_at)
        return ScanResponse(status="unknown", message="Card not registered")

    if not card.active:
        member = db.query(Member).filter(Member.id == card.member_id).first()
        _log_scan(db, uid, device.id, ScanResult.inactive, start_time, req.scanned_at)
        return ScanResponse(
            status="inactive",
            name=member.name if member else None,
            message="Card deactivated (lost/stolen)",
        )

    # ── Step 4: Check membership ──
    membership = (
        db.query(Membership)
        .filter(Membership.member_id == card.member_id)
        .order_by(Membership.end_date.desc())
        .first()
    )

    ist_now = _now_ist()
    today_ist = ist_now.date()

    member = db.query(Member).filter(Member.id == card.member_id).first()
    member_name = member.name if member else "Unknown"

    if not membership or membership.end_date < today_ist:
        _log_scan(db, uid, device.id, ScanResult.expired, start_time, req.scanned_at)
        return ScanResponse(
            status="expired",
            name=member_name,
            expiry_date=membership.end_date if membership else None,
            message="Membership expired",
        )

    # ── Step 5: Mark attendance ──
    # Use the device-provided timestamp for offline-queued taps,
    # otherwise use current time.
    if req.scanned_at:
        checkin_time = req.scanned_at
        # For offline taps, use the IST date of the original scan
        if req.scanned_at.tzinfo is None:
            scan_ist = req.scanned_at.replace(tzinfo=timezone.utc).astimezone(IST)
        else:
            scan_ist = req.scanned_at.astimezone(IST)
        attendance_date = scan_ist.date()
    else:
        checkin_time = datetime.now(timezone.utc)
        attendance_date = today_ist

    attendance = Attendance(
        member_id=card.member_id,
        attendance_date=attendance_date,
        checkin_time=checkin_time,
    )

    try:
        db.add(attendance)
        db.commit()
        result = ScanResult.marked
    except IntegrityError:
        # UNIQUE(member_id, attendance_date) violation → already checked in today
        db.rollback()
        result = ScanResult.already_marked

    _log_scan(db, uid, device.id, result, start_time, req.scanned_at)
    return ScanResponse(
        status=result.value,
        name=member_name,
        expiry_date=membership.end_date,
    )
