"""
All SQLAlchemy ORM models for the Fitness Temple RFID system.

Design notes:
- Timestamps stored in UTC (server_default=func.now() uses MySQL's UTC_TIMESTAMP
  when the connection timezone is set to UTC). Business logic converts to IST.
- `extra` column on members uses MySQL's JSON type for flexible additional fields
  (e.g., emergency_contact, blood_group) without schema changes.
- attendance has a UNIQUE(member_id, attendance_date) constraint so the /scan
  endpoint can rely on IntegrityError for idempotent deduplication instead of
  check-then-insert (which has a TOCTOU race).
- memberships are append-only. "Current" membership = row with MAX(end_date).
- cards table tracks the full history of card assignments; only one card per
  member can be active at a time (enforced in application logic, not DB,
  because MySQL doesn't support partial unique indexes).
"""

import enum

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index, Enum, Numeric,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ── Enums ──

class ScanResult(str, enum.Enum):
    """Every possible outcome of a card tap."""
    marked = "marked"
    already_marked = "already_marked"
    expired = "expired"
    unknown = "unknown"
    inactive = "inactive"
    linked = "linked"
    rejected = "rejected"


class AssignmentStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    expired = "expired"


# ── Models ──

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    secret_key_hash = Column(String(255), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    active = Column(Boolean, default=True, nullable=False)


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    address = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)  # flexible extra fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships for convenience (not used in /scan hot path)
    memberships = relationship("Membership", back_populates="member", lazy="dynamic")
    cards = relationship("Card", back_populates="member", lazy="dynamic")
    attendances = relationship("Attendance", back_populates="member", lazy="dynamic")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    amount_paid = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    member = relationship("Member", back_populates="memberships")
    plan = relationship("Plan")

    __table_args__ = (
        # Speed up "get latest membership for a member" query
        Index("ix_memberships_member_end", "member_id", "end_date"),
    )


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(20), unique=True, nullable=False)  # hex string, e.g. "A1B2C3D4"
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    assigned_at = Column(DateTime, server_default=func.now(), nullable=False)
    deactivated_at = Column(DateTime, nullable=True)

    member = relationship("Member", back_populates="cards")

    __table_args__ = (
        # Fast lookup by UID (already unique, but explicit index name)
        Index("ix_cards_uid", "uid"),
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    checkin_time = Column(DateTime, nullable=False)

    member = relationship("Member", back_populates="attendances")

    __table_args__ = (
        # Core constraint: one check-in per member per day.
        # /scan relies on IntegrityError from this to return "already_marked".
        UniqueConstraint("member_id", "attendance_date", name="uq_member_date"),
        Index("ix_attendance_date", "attendance_date"),
    )


class ScanLog(Base):
    __tablename__ = "scan_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(20), nullable=True)  # null if device key was wrong
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    result = Column(Enum(ScanResult), nullable=False)
    response_ms = Column(Integer, nullable=True)
    scanned_at = Column(DateTime, server_default=func.now(), nullable=False)


class PendingAssignment(Base):
    __tablename__ = "pending_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(Enum(AssignmentStatus), default=AssignmentStatus.pending, nullable=False)

    member = relationship("Member")
