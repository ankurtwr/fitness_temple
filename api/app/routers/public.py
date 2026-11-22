"""
Public routes for prospective gym members and general visitors.
- GET /explore: Showcase landing page with scroll-driven kinetic UI
- GET /media: Interactive 3D tilt & shutter iris reveal media gallery
- GET /api/public/info: Public stats & plan pricing (no private member data)
- GET /app: Mobile PWA admin app
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attendance, Plan

router = APIRouter()


@router.get("/app", include_in_schema=False)
def mobile_app(request: Request):
    """Serve the mobile PWA — works on any phone browser, no app install needed."""
    from app.main import templates
    from app.dependencies import get_session
    session = get_session(request)
    cookie_token = request.cookies.get("session", "") if session else ""
    username = session.get("username", "") if session else ""
    return templates.TemplateResponse(
        request=request,
        name="mobile_app.html",
        context={"initial_token": cookie_token, "initial_username": username},
    )

IST = timezone(timedelta(hours=5, minutes=30))


def _today_ist():
    return datetime.now(IST).date()


def _ensure_static_assets():
    import os, shutil, glob
    from pathlib import Path
    static_img = Path(__file__).resolve().parent.parent / "static" / "img"
    static_img.mkdir(parents=True, exist_ok=True)
    
    brain_dirs = [
        Path(r"C:\Users\Anuj\.gemini\antigravity-ide\brain\8bd5c50b-1175-4e97-aa88-78ec69ee7b60"),
        Path(r"C:\Users\Anuj\.gemini\antigravity-ide\brain\3cff87c6-a456-462e-a7c4-603850fab267"),
    ]
    
    aliases = {
        "hero_athlete.jpg": ["hero_bodybuilder_*.jpg"],
        "program_strength.jpg": ["program_strength_*.jpg"],
        "program_muscle.jpg": ["program_muscle_*.jpg"],
        "program_trainer.jpg": ["program_trainer_*.jpg"],
        "bench_lockout.jpg": ["bench_press_phase1_*.jpg"],
        "bench_bottom.jpg": ["bench_press_bottom_*.jpg"],
        "bench_phase2.jpg": ["bench_press_phase2_*.jpg"],
        "gym_strength_zone.jpg": ["gym_strength_zone_*.jpg"],
        "gym_cardio_deck.jpg": ["gym_cardio_deck_*.jpg"],
        "gym_functional_zone.jpg": ["gym_functional_zone_*.jpg"],
        "gym_recovery_spa.jpg": ["gym_recovery_spa_*.jpg"],
    }
    
    for b_dir in brain_dirs:
        if not b_dir.exists():
            continue
        for dest, patterns in aliases.items():
            dest_file = static_img / dest
            if not dest_file.exists():
                for pattern in patterns:
                    matches = list(b_dir.glob(pattern))
                    if matches:
                        try:
                            shutil.copy(matches[0], dest_file)
                        except Exception:
                            pass


_ensure_static_assets()


@router.get("/explore", response_class=HTMLResponse)
def public_explore_page(request: Request, db: Session = Depends(get_db)):
    """Public gym showcase page with scroll animations and membership plans."""
    _ensure_static_assets()
    from app.main import templates
    plans = db.query(Plan).filter(Plan.active == True).all()
    today = _today_ist()
    today_count = db.query(Attendance).filter(Attendance.attendance_date == today).count()

    return templates.TemplateResponse(
        request=request,
        name="explore.html",
        context={
            "plans": plans,
            "today_count": today_count,
        },
    )


@router.get("/media", response_class=HTMLResponse)
def public_media_page(request: Request):
    """Interactive media gallery page with 3D tilt, categories, and iris lightbox."""
    from app.main import templates
    return templates.TemplateResponse(
        request=request,
        name="media.html",
        context={},
    )


@router.get("/api/public/info")
def get_public_info(db: Session = Depends(get_db)):
    """Safe public endpoint returning live check-in count and membership plan rates."""
    today = _today_ist()
    count = db.query(Attendance).filter(Attendance.attendance_date == today).count()
    plans = db.query(Plan).filter(Plan.active == True).all()
    return {
        "today_checkins": count,
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "duration_days": p.duration_days,
                "price": float(p.price),
            }
            for p in plans
        ],
    }
