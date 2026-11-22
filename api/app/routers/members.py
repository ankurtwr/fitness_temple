"""
Member management routes:
- Members list page + search API
- Member profile page + details API
- Register member (create + first membership)
- Card assignment flow (pending_assignment → /scan links it)
- Renewal
- Lost/stolen card reporting
"""

from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.dependencies import (
    require_admin_page, require_admin_api,
    generate_csrf_token, verify_csrf_token,
)
from app.models import (
    Member, Membership, Card, Plan, Attendance,
    PendingAssignment, AssignmentStatus,
)
from app.config import settings

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


def _today_ist():
    return datetime.now(IST).date()


def _get_latest_membership(db: Session, member_id: int) -> Membership | None:
    return (
        db.query(Membership)
        .filter(Membership.member_id == member_id)
        .order_by(Membership.end_date.desc())
        .first()
    )


def _get_active_card(db: Session, member_id: int) -> Card | None:
    return (
        db.query(Card)
        .filter(Card.member_id == member_id, Card.active == True)
        .first()
    )


# ═══════════════════════════════════════════
#  Pages
# ═══════════════════════════════════════════

@router.get("/members", response_class=HTMLResponse)
def members_page(request: Request, admin=Depends(require_admin_page)):
    from app.main import templates
    return templates.TemplateResponse(
        request=request,
        name="members.html",
        context={
            "admin": admin,
            "csrf_token": generate_csrf_token(request),
        },
    )


@router.get("/members/{member_id}", response_class=HTMLResponse)
def member_profile_page(
    member_id: int, request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_page),
):
    from app.main import templates

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return RedirectResponse(url="/members", status_code=303)

    membership = _get_latest_membership(db, member_id)
    active_card = _get_active_card(db, member_id)
    today = _today_ist()

    # Last 30 days attendance
    thirty_days_ago = today - timedelta(days=30)
    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.member_id == member_id,
            Attendance.attendance_date >= thirty_days_ago,
        )
        .order_by(Attendance.attendance_date.desc())
        .all()
    )

    # All memberships for history
    all_memberships = (
        db.query(Membership, Plan)
        .join(Plan, Membership.plan_id == Plan.id)
        .filter(Membership.member_id == member_id)
        .order_by(Membership.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="member_profile.html",
        context={
            "admin": admin,
            "member": member,
            "membership": membership,
            "active_card": active_card,
            "is_expired": (membership.end_date < today) if membership else True,
            "attendance_records": attendance_records,
            "all_memberships": all_memberships,
            "days_in_30": sum(1 for a in attendance_records),
            "csrf_token": generate_csrf_token(request),
        },
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin_page)):
    from app.main import templates
    plans = db.query(Plan).filter(Plan.active == True).all()
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "admin": admin,
            "plans": plans,
            "csrf_token": generate_csrf_token(request),
        },
    )


@router.get("/renew", response_class=HTMLResponse)
def renew_page(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin_page)):
    from app.main import templates
    plans = db.query(Plan).filter(Plan.active == True).all()
    return templates.TemplateResponse(
        request=request,
        name="renew.html",
        context={
            "admin": admin,
            "plans": plans,
            "csrf_token": generate_csrf_token(request),
        },
    )


@router.get("/assign-card/{member_id}", response_class=HTMLResponse)
def assign_card_page(
    member_id: int, request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_page),
):
    from app.main import templates
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return RedirectResponse(url="/members", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="assign_card.html",
        context={
            "admin": admin,
            "member": member,
            "csrf_token": generate_csrf_token(request),
        },
    )


@router.get("/report-lost/{member_id}", response_class=HTMLResponse)
def report_lost_page(
    member_id: int, request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_page),
):
    from app.main import templates
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return RedirectResponse(url="/members", status_code=303)
    active_card = _get_active_card(db, member_id)
    return templates.TemplateResponse(
        request=request,
        name="report_lost.html",
        context={
            "admin": admin,
            "member": member,
            "active_card": active_card,
            "csrf_token": generate_csrf_token(request),
        },
    )


# ═══════════════════════════════════════════
#  API endpoints
# ═══════════════════════════════════════════

@router.get("/api/members")
def search_members(
    search: str = Query("", max_length=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """Search members by name or phone. Returns list for table/dropdown."""
    query = db.query(Member)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(Member.name.ilike(pattern), Member.phone.ilike(pattern))
        )
    members = query.order_by(Member.name).limit(100).all()

    today = _today_ist()
    results = []
    for m in members:
        ms = _get_latest_membership(db, m.id)
        card = _get_active_card(db, m.id)
        if not ms:
            status = "expired"
            days_left = -1
        else:
            days_left = (ms.end_date - today).days
            if days_left < 0:
                status = "expired"
            elif days_left <= 3:
                status = "expiring_soon"
            else:
                status = "active"

        results.append({
            "id": m.id,
            "name": m.name,
            "phone": m.phone,
            "current_plan": ms.plan.name if ms and ms.plan else None,
            "expiry_date": ms.end_date.isoformat() if ms else None,
            "days_left": days_left,
            "status": status,
            "is_expired": status == "expired",
            "has_active_card": card is not None,
            "card_uid": card.uid if card else None,
        })
    return {"members": results}


@router.get("/api/members/{member_id}")
def get_member_details(
    member_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return {"error": "Member not found"}, 404

    ms = _get_latest_membership(db, member_id)
    card = _get_active_card(db, member_id)
    today = _today_ist()

    if not ms:
        status = "expired"
        days_left = -1
    else:
        days_left = (ms.end_date - today).days
        if days_left < 0:
            status = "expired"
        elif days_left <= 3:
            status = "expiring_soon"
        else:
            status = "active"

    # Payment / renewal history for every month
    all_memberships = (
        db.query(Membership, Plan)
        .join(Plan, Membership.plan_id == Plan.id)
        .filter(Membership.member_id == member_id)
        .order_by(Membership.start_date.desc(), Membership.id.desc())
        .all()
    )
    payments = [
        {
            "id": m_row.id,
            "plan_name": p_row.name,
            "amount_paid": float(m_row.amount_paid),
            "start_date": m_row.start_date.isoformat(),
            "end_date": m_row.end_date.isoformat(),
            "date": m_row.created_at.strftime("%d %b %Y") if m_row.created_at else str(m_row.start_date),
        }
        for m_row, p_row in all_memberships
    ]

    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "address": member.address,
        "expiry_date": ms.end_date.isoformat() if ms else None,
        "days_left": days_left,
        "status": status,
        "is_expired": status == "expired",
        "plan_name": ms.plan.name if ms and ms.plan else None,
        "has_active_card": card is not None,
        "card_uid": card.uid if card else None,
        "payments": payments,
    }


@router.delete("/api/members/{member_id}")
@router.post("/api/members/{member_id}/delete")
def delete_member(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """Permanently delete a member and all their records."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return {"error": "Member not found"}, 404
    name = member.name
    db.query(Attendance).filter(Attendance.member_id == member_id).delete()
    db.query(Membership).filter(Membership.member_id == member_id).delete()
    db.query(Card).filter(Card.member_id == member_id).delete()
    db.query(PendingAssignment).filter(PendingAssignment.member_id == member_id).delete()
    db.delete(member)
    db.commit()
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/members", status_code=303)
    return {"success": True, "message": f"Member {name} permanently deleted"}


@router.post("/api/members/{member_id}/revoke-card")
def revoke_card(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """Revoke/deactivate active card for a member."""
    card = _get_active_card(db, member_id)
    if not card:
        return {"error": "No active card to revoke"}
    card.active = False
    card.deactivated_at = datetime.utcnow()
    db.commit()
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url=f"/members/{member_id}", status_code=303)
    return {"success": True, "message": f"Card {card.uid} revoked"}


@router.post("/api/members")
def create_member(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(""),
    extra_json: str = Form("{}"),
    plan_id: int = Form(...),
    amount_paid: float = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """Create a new member with their first membership."""
    verify_csrf_token(request, csrf_token)

    import json
    try:
        extra = json.loads(extra_json) if extra_json and extra_json.strip() != "{}" else None
    except json.JSONDecodeError:
        extra = None

    # Check duplicate phone
    existing = db.query(Member).filter(Member.phone == phone).first()
    if existing:
        return {"error": f"Phone {phone} already registered to {existing.name}"}

    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        return {"error": "Invalid plan"}

    # Create member
    member = Member(name=name, phone=phone, address=address or None, extra=extra)
    db.add(member)
    db.flush()  # get member.id

    # Create first membership
    today = _today_ist()
    membership = Membership(
        member_id=member.id,
        plan_id=plan.id,
        start_date=today,
        end_date=today + timedelta(days=plan.duration_days),
        amount_paid=amount_paid,
    )
    db.add(membership)
    db.commit()

    return {
        "success": True,
        "member_id": member.id,
        "message": f"Member {name} registered successfully",
    }


@router.post("/api/members/{member_id}/renew")
def renew_membership(
    member_id: int,
    request: Request,
    plan_id: int = Form(...),
    amount_paid: float = Form(0),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """
    Renew a membership. Date rule:
    - If current end_date >= today → new start = end_date + 1 day
    - Else → new start = today
    This way members don't lose remaining days if they renew early.
    """
    verify_csrf_token(request, csrf_token)

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return {"error": "Member not found"}

    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        return {"error": "Invalid plan"}

    today = _today_ist()
    current = _get_latest_membership(db, member_id)

    # Renewal date rule
    if current and current.end_date >= today:
        start_date = current.end_date + timedelta(days=1)
    else:
        start_date = today

    end_date = start_date + timedelta(days=plan.duration_days)
    final_amount = amount_paid if amount_paid > 0 else float(plan.price)

    membership = Membership(
        member_id=member_id,
        plan_id=plan.id,
        start_date=start_date,
        end_date=end_date,
        amount_paid=final_amount,
    )
    db.add(membership)
    db.commit()

    return {
        "success": True,
        "message": f"Membership renewed for {member.name} until {end_date}",
        "end_date": end_date.isoformat(),
    }


@router.post("/api/members/{member_id}/assign-card")
def start_card_assignment(
    member_id: int,
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """
    Create a pending_assignment. The next new UID tapped on any
    reader within 30 seconds gets linked to this member.
    """
    verify_csrf_token(request, csrf_token)

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return {"error": "Member not found"}

    # Cancel any existing pending assignments for this member
    db.query(PendingAssignment).filter(
        PendingAssignment.member_id == member_id,
        PendingAssignment.status == AssignmentStatus.pending,
    ).update({"status": AssignmentStatus.expired})

    ttl = settings.CARD_ASSIGN_TTL_SECONDS
    assignment = PendingAssignment(
        member_id=member_id,
        expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        status=AssignmentStatus.pending,
    )
    db.add(assignment)
    db.commit()

    return {
        "success": True,
        "assignment_id": assignment.id,
        "expires_in_seconds": ttl,
        "message": f"Waiting for card tap for {member.name}...",
    }


@router.get("/api/assign/status")
def check_assignment_status(
    assignment_id: int = Query(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """Polled every second by the assign-card page."""
    assignment = db.query(PendingAssignment).filter(
        PendingAssignment.id == assignment_id
    ).first()

    if not assignment:
        return {"status": "expired", "message": "Assignment not found"}

    # Check if it expired by time
    now_utc = datetime.utcnow()
    expires_at = assignment.expires_at
    if expires_at and expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    is_time_expired = (expires_at < now_utc) if expires_at else True

    if assignment.status == AssignmentStatus.pending and is_time_expired:
        assignment.status = AssignmentStatus.expired
        db.commit()

    member = db.query(Member).filter(Member.id == assignment.member_id).first()

    if assignment.status == AssignmentStatus.done:
        card = _get_active_card(db, assignment.member_id)
        return {
            "status": "done",
            "member_name": member.name if member else None,
            "card_uid": card.uid if card else None,
            "message": "Card assigned successfully!",
        }

    return {
        "status": assignment.status.value,
        "member_name": member.name if member else None,
    }


@router.post("/api/members/{member_id}/report-lost")
def report_lost_card(
    member_id: int,
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_api),
):
    """Deactivate the member's current active card."""
    verify_csrf_token(request, csrf_token)

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return {"error": "Member not found"}

    card = _get_active_card(db, member_id)
    if not card:
        return {"error": "No active card to deactivate"}

    card.active = False
    card.deactivated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "message": f"Card {card.uid} deactivated for {member.name}",
        "member_id": member_id,
    }


@router.get("/api/plans")
def get_plans(db: Session = Depends(get_db), admin=Depends(require_admin_api)):
    plans = db.query(Plan).filter(Plan.active == True).all()
    return {
        "plans": [
            {"id": p.id, "name": p.name, "duration_days": p.duration_days, "price": float(p.price)}
            for p in plans
        ]
    }
