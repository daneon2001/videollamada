import enum
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    JSON,
    Index,
    Enum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .db import Base


class UserRole(enum.Enum):
    doctor = "doctor"
    patient = "patient"


class CallStatus(enum.Enum):
    waiting = "waiting"
    assigned = "assigned"
    ringing = "ringing"
    in_progress = "in_progress"
    reconnecting = "reconnecting"
    ended = "ended"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String(64), primary_key=True)  # room_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    active = Column(Boolean, default=True)


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(64), ForeignKey("rooms.id"), index=True)
    patient_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("users.id"), index=True)
    status = Column(Enum(CallStatus), default=CallStatus.waiting, index=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    assigned_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    last_resume_at = Column(DateTime(timezone=True))
    total_reconnects = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    meta = Column(JSON, nullable=True)

    room = relationship("Room")
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(64), ForeignKey("rooms.id"), index=True)
    sid = Column(String(120), index=True)  # socket id
    user_id = Column(String(120), ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True))

    room = relationship("Room")
    user = relationship("User")


Index("ix_participants_room_sid", Participant.room_id, Participant.sid, unique=True)
