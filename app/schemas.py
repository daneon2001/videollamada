from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    doctor = "doctor"
    patient = "patient"


class CallStatus(str, Enum):
    waiting = "waiting"
    assigned = "assigned"
    ringing = "ringing"
    in_progress = "in_progress"
    reconnecting = "reconnecting"
    ended = "ended"
    cancelled = "cancelled"


class Health(BaseModel):
    status: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: Role


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    is_available: bool

    class Config:
        from_attributes = True


class AvailabilityUpdate(BaseModel):
    is_available: bool


class JoinResponse(BaseModel):
    ok: bool
    peers: List[str] = Field(default_factory=list)


class CallRequestCreate(BaseModel):
    room_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CallDetail(BaseModel):
    id: int
    room_id: str
    patient_id: str
    doctor_id: Optional[str]
    status: CallStatus
    requested_at: datetime
    started_at: Optional[datetime]
    assigned_at: Optional[datetime]
    ended_at: Optional[datetime]
    last_resume_at: Optional[datetime]
    total_reconnects: int
    duration_seconds: int
    meta: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class CallResumePayload(BaseModel):
    note: Optional[str] = None


class MetricsResponse(BaseModel):
    total_calls: int
    waiting: int
    in_progress: int
    ended: int
    avg_duration_seconds: float
    avg_reconnects: float
