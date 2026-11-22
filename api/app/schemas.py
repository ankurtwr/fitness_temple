"""
Pydantic schemas for request/response validation.
Separated from ORM models (schemas = API shape, models = DB shape).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Scan (Phase 2) ──

class ScanRequest(BaseModel):
    uid: str = Field(..., min_length=4, max_length=20, description="RFID card UID hex string")
    device_key: str = Field(..., min_length=1, description="Device secret key")
    scanned_at: Optional[datetime] = Field(None, description="Original scan time for offline-queued taps")


class ScanResponse(BaseModel):
    status: str
    name: Optional[str] = None
    expiry_date: Optional[date] = None
    message: Optional[str] = None


# ── Auth (Phase 3) ──

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


# ── Members (Phase 4-6) ──

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    address: Optional[str] = None
    extra: Optional[dict] = None
    plan_id: int
    amount_paid: Decimal = Field(..., ge=0)


class MemberOut(BaseModel):
    id: int
    name: str
    phone: str
    address: Optional[str] = None
    extra: Optional[dict] = None
    created_at: datetime
    current_plan: Optional[str] = None
    expiry_date: Optional[date] = None
    is_expired: bool = False
    has_active_card: bool = False

    model_config = {"from_attributes": True}


class MemberSearchResult(BaseModel):
    id: int
    name: str
    phone: str


class RenewRequest(BaseModel):
    plan_id: int
    amount_paid: Optional[Decimal] = None  # defaults to plan price if not given


class AttendanceRow(BaseModel):
    id: int
    member_id: int
    name: str
    checkin_time: datetime
    expiry_date: Optional[date] = None
    is_expired: bool = False


class AssignmentStatusOut(BaseModel):
    status: str  # pending, done, expired
    member_name: Optional[str] = None


class PlanOut(BaseModel):
    id: int
    name: str
    duration_days: int
    price: Decimal

    model_config = {"from_attributes": True}
