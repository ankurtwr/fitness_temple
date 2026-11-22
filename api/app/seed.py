"""
Seed script: creates default plans, admin user, and test device.
Run via:  python -m app.seed
Idempotent — safe to run multiple times.
"""

from sqlalchemy.orm import Session
import bcrypt

from app.database import SessionLocal
from app.models import Plan, Admin, Device
from app.config import settings
from app.dependencies import hash_device_key


# ── Default gym plans ──
DEFAULT_PLANS = [
    {"name": "1 Month",   "duration_days": 30,  "price": 1000},
    {"name": "3 Months",  "duration_days": 90,  "price": 2000},
    {"name": "6 Months",  "duration_days": 180, "price": 4000},
    {"name": "12 Months", "duration_days": 365, "price": 7000},
]

# ── Default device for testing (key = "testdevice123") ──
DEFAULT_DEVICE_NAME = "entrance-reader-1"
DEFAULT_DEVICE_KEY = "testdevice123"


def seed_plans(db: Session) -> None:
    if db.query(Plan).first() is not None:
        print("Plans already seeded, skipping.")
        return
    for plan_data in DEFAULT_PLANS:
        db.add(Plan(**plan_data))
    db.commit()
    print(f"Seeded {len(DEFAULT_PLANS)} plans.")


def seed_admin(db: Session) -> None:
    existing = db.query(Admin).filter(Admin.username == settings.ADMIN_USERNAME).first()
    if existing:
        print(f"Admin '{settings.ADMIN_USERNAME}' already exists, skipping.")
        return
    admin = Admin(
        username=settings.ADMIN_USERNAME,
        password_hash=bcrypt.hashpw(settings.ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
    )
    db.add(admin)
    db.commit()
    print(f"Created admin user: {settings.ADMIN_USERNAME}")


def seed_device(db: Session) -> None:
    """
    Device keys use SHA-256 (not bcrypt) for fast verification
    in the /scan hot path. See dependencies.py for rationale.
    """
    existing = db.query(Device).filter(Device.name == DEFAULT_DEVICE_NAME).first()
    if existing:
        print(f"Device '{DEFAULT_DEVICE_NAME}' already exists, skipping.")
        return
    device = Device(
        name=DEFAULT_DEVICE_NAME,
        secret_key_hash=hash_device_key(DEFAULT_DEVICE_KEY),
    )
    db.add(device)
    db.commit()
    print(f"Created device: {DEFAULT_DEVICE_NAME} (key: {DEFAULT_DEVICE_KEY})")


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_plans(db)
        seed_admin(db)
        seed_device(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
