"""
Dashboard routes: live attendance home page + attendance polling API.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin_page, require_admin_api
from app.models import Attendance, Member, Membership

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


def _today_ist():
    return datetime.now(IST).date()


def _build_attendance_row(att, member, membership):
    """Build a dict for one attendance row with shift and status color."""
    today = _today_ist()
    if not membership:
        status = "expired"
        days_left = -1
    else:
        days_left = (membership.end_date - today).days
        if days_left < 0:
            status = "expired"        # Red
        elif days_left <= 3:
            status = "expiring_soon"  # Yellow
        else:
            status = "active"         # Green

    checkin_ist = att.checkin_time
    if checkin_ist:
        if checkin_ist.tzinfo is None:
            checkin_ist = checkin_ist.replace(tzinfo=timezone.utc).astimezone(IST)
        else:
            checkin_ist = checkin_ist.astimezone(IST)
        shift = "morning" if checkin_ist.hour < 13 else "evening"
        time_str = checkin_ist.strftime("%I:%M %p")
    else:
        shift = "morning"
        time_str = "--"

    return {
        "id": att.id,
        "member_id": att.member_id,
        "name": member.name if member else "Unknown",
        "checkin_time": att.checkin_time.isoformat() if att.checkin_time else None,
        "time_str": time_str,
        "shift": shift,
        "expiry_date": membership.end_date.isoformat() if membership else None,
        "days_left": days_left,
        "status": status,
        "is_expired": status == "expired",
    }


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request, admin=Depends(require_admin_page)):
    """Render the live attendance dashboard with today's data."""
    from app.main import templates
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"admin": admin, "active_page": "home"},
    )


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, admin=Depends(require_admin_page)):
    """Day-wise attendance log page for the gym owner."""
    from app.main import templates
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={"admin": admin, "active_page": "logs"},
    )


@router.get("/api/attendance/today")
def get_today_attendance(
    since_id: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """
    Return today's attendance rows with id > since_id.
    Polled every 2 seconds by the home page JS.
    """
    today = _today_ist()

    rows = (
        db.query(Attendance, Member)
        .join(Member, Attendance.member_id == Member.id)
        .filter(
            Attendance.attendance_date == today,
            Attendance.id > since_id,
        )
        .order_by(Attendance.id.asc())
        .all()
    )

    results = []
    for att, member in rows:
        membership = (
            db.query(Membership)
            .filter(Membership.member_id == member.id)
            .order_by(Membership.end_date.desc())
            .first()
        )
        results.append(_build_attendance_row(att, member, membership))

    return {"rows": results}


@router.get("/api/attendance/logs")
def get_attendance_logs(
    target_date: str = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """
    Day-wise attendance logs broken down by Morning and Evening shifts.
    """
    if target_date:
        try:
            req_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            req_date = _today_ist()
    else:
        req_date = _today_ist()

    rows = (
        db.query(Attendance, Member)
        .join(Member, Attendance.member_id == Member.id)
        .filter(Attendance.attendance_date == req_date)
        .order_by(Attendance.checkin_time.asc())
        .all()
    )

    all_rows = []
    morning_rows = []
    evening_rows = []

    for att, member in rows:
        membership = (
            db.query(Membership)
            .filter(Membership.member_id == member.id)
            .order_by(Membership.end_date.desc())
            .first()
        )
        row = _build_attendance_row(att, member, membership)
        all_rows.append(row)
        if row["shift"] == "morning":
            morning_rows.append(row)
        else:
            evening_rows.append(row)

    return {
        "date": req_date.isoformat(),
        "total_count": len(all_rows),
        "morning_count": len(morning_rows),
        "evening_count": len(evening_rows),
        "morning": morning_rows,
        "evening": evening_rows,
        "all": all_rows,
    }
