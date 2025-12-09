import json
import uuid
from datetime import datetime
from typing import List

import socketio
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas
from .config import settings
from .db import init_db
from .deps import get_db
from .schemas import Health
from .security import (
    create_access_token,
    get_current_active_user,
    get_password_hash,
    require_role,
    verify_password,
)

# -------------------------------------------------------------------
# Normalizar ALLOWED_ORIGINS a una lista de strings
# -------------------------------------------------------------------
raw_origins = settings.ALLOWED_ORIGINS

if isinstance(raw_origins, str):
    try:
        parsed = json.loads(raw_origins)
        if isinstance(parsed, str):
            origins = [parsed]
        else:
            origins = list(parsed)
    except Exception:
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
elif isinstance(raw_origins, (list, tuple, set)):
    origins = list(raw_origins)
else:
    origins = ["*"]

cors_origins = ["*"] if "*" in origins else origins
print("CORS origins usados:", cors_origins)

# -------------------------------------------------------------------
# Socket.IO (ASGI)
# -------------------------------------------------------------------
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    engineio_logger=True,
    logger=True
)

# -------------------------------------------------------------------
# API FastAPI
# -------------------------------------------------------------------
api = FastAPI(title="Video API")


@api.on_event("startup")
async def on_startup():
    init_db()

api.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_call_or_404(db: Session, call_id: int) -> models.Call:
    call = db.get(models.Call, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@api.get("/health", response_model=Health)
def health():
    return {"status": "ok"}


@api.get("/config/ice")
@api.get("/ice")
def ice_config():
    servers = [{"urls": settings.STUN_URLS}]
    if settings.TURN_URLS:
        servers.append(
            {
                "urls": settings.TURN_URLS,
                "username": settings.TURN_USERNAME,
                "credential": settings.TURN_CREDENTIAL,
            }
        )
    return {"iceServers": servers}


# -------------------------------------------------------------------
# Auth & usuarios
# -------------------------------------------------------------------
@api.post("/auth/register", response_model=schemas.UserRead)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    user_exists = db.query(models.User).filter(
        models.User.email == user_in.email.lower()
    ).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    model = models.User(
        email=user_in.email.lower(),
        full_name=user_in.full_name,
        role=models.UserRole(user_in.role.value),
        password_hash=get_password_hash(user_in.password),
        is_available=user_in.role == schemas.Role.doctor,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@api.post("/auth/token", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = (
        db.query(models.User)
        .filter(models.User.email == form_data.username.lower())
        .first()
    )
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}


@api.get("/users/me", response_model=schemas.UserRead)
async def read_users_me(current_user=Depends(get_current_active_user)):
    return current_user


@api.patch("/users/me/availability", response_model=schemas.UserRead)
async def update_availability(
    payload: schemas.AvailabilityUpdate,
    current_user=Depends(require_role(models.UserRole.doctor)),
    db: Session = Depends(get_db),
):
    current_user.is_available = payload.is_available
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


# -------------------------------------------------------------------
# Orquestación de llamadas
# -------------------------------------------------------------------
@api.post("/calls/request", response_model=schemas.CallDetail)
async def request_call(
    payload: schemas.CallRequestCreate,
    patient=Depends(require_role(models.UserRole.patient)),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(models.Call)
        .filter(
            models.Call.patient_id == patient.id,
            models.Call.status.in_(
                [models.CallStatus.waiting, models.CallStatus.assigned, models.CallStatus.in_progress]
            ),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Patient already has an active call request"
        )

    room_id = payload.room_id or f"room-{uuid.uuid4().hex[:10]}"

    room = db.get(models.Room, room_id)
    if not room:
        room = models.Room(id=room_id)
        db.add(room)
        db.flush()

    call = models.Call(
        room_id=room_id,
        patient_id=patient.id,
        status=models.CallStatus.waiting,
        meta=payload.metadata,
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@api.get("/calls/waiting", response_model=List[schemas.CallDetail])
async def list_waiting_calls(
    doctor=Depends(require_role(models.UserRole.doctor)), db: Session = Depends(get_db)
):
    _ = doctor  # no-op, solo valida el rol
    calls = (
        db.query(models.Call)
        .filter(models.Call.status == models.CallStatus.waiting)
        .order_by(models.Call.requested_at.asc())
        .all()
    )
    return calls


@api.post("/calls/{call_id}/claim", response_model=schemas.CallDetail)
async def claim_call(
    call_id: int,
    doctor=Depends(require_role(models.UserRole.doctor)),
    db: Session = Depends(get_db),
):
    call = _get_call_or_404(db, call_id)
    if call.status != models.CallStatus.waiting:
        raise HTTPException(status_code=400, detail="Call is not available")

    call.doctor_id = doctor.id
    call.status = models.CallStatus.assigned
    call.assigned_at = datetime.utcnow()
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@api.post("/calls/{call_id}/start", response_model=schemas.CallDetail)
async def start_call(
    call_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    call = _get_call_or_404(db, call_id)
    if call.status not in (
        models.CallStatus.assigned,
        models.CallStatus.waiting,
        models.CallStatus.in_progress,
    ):
        raise HTTPException(status_code=400, detail="Call already started")

    if current_user.id not in (call.patient_id, call.doctor_id):
        raise HTTPException(status_code=403, detail="User not part of this call")

    if call.started_at is None or call.status == models.CallStatus.waiting:
        call.started_at = datetime.utcnow()
    call.status = models.CallStatus.in_progress
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@api.post("/calls/{call_id}/resume", response_model=schemas.CallDetail)
async def resume_call(
    call_id: int,
    payload: schemas.CallResumePayload,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    call = _get_call_or_404(db, call_id)
    if call.status == models.CallStatus.ended:
        raise HTTPException(status_code=400, detail="Call already finished")
    if current_user.id not in (call.patient_id, call.doctor_id):
        raise HTTPException(status_code=403, detail="User not part of this call")

    call.status = models.CallStatus.in_progress
    call.total_reconnects += 1
    call.last_resume_at = datetime.utcnow()
    if payload.note:
        meta = call.meta or {}
        resumes = meta.setdefault("resumes", [])
        resumes.append({"at": datetime.utcnow().isoformat(), "note": payload.note})
        call.meta = meta
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@api.post("/calls/{call_id}/end", response_model=schemas.CallDetail)
async def end_call(
    call_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    call = _get_call_or_404(db, call_id)
    if current_user.id not in (call.patient_id, call.doctor_id):
        raise HTTPException(status_code=403, detail="User not part of this call")

    if call.status == models.CallStatus.ended:
        return call

    if call.ended_at:
        return call

    call.status = models.CallStatus.ended
    call.ended_at = datetime.utcnow()
    if call.started_at and call.ended_at:
        call.duration_seconds = int(
            (call.ended_at - call.started_at).total_seconds()
        )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@api.get("/calls/{call_id}", response_model=schemas.CallDetail)
async def get_call(
    call_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    call = _get_call_or_404(db, call_id)
    if current_user.id not in (call.patient_id, call.doctor_id):
        raise HTTPException(status_code=403, detail="User not part of this call")
    return call


# -------------------------------------------------------------------
# Métricas
# -------------------------------------------------------------------
@api.get("/metrics/calls", response_model=schemas.MetricsResponse)
async def call_metrics(
    doctor=Depends(require_role(models.UserRole.doctor)), db: Session = Depends(get_db)
):
    _ = doctor
    total_calls = db.query(func.count(models.Call.id)).scalar() or 0
    waiting = (
        db.query(func.count(models.Call.id))
        .filter(models.Call.status == models.CallStatus.waiting)
        .scalar()
        or 0
    )
    in_progress = (
        db.query(func.count(models.Call.id))
        .filter(models.Call.status == models.CallStatus.in_progress)
        .scalar()
        or 0
    )
    ended = (
        db.query(func.count(models.Call.id))
        .filter(models.Call.status == models.CallStatus.ended)
        .scalar()
        or 0
    )
    avg_duration = (
        db.query(func.avg(models.Call.duration_seconds))
        .filter(models.Call.duration_seconds > 0)
        .scalar()
        or 0
    )
    avg_reconnects = (
        db.query(func.avg(models.Call.total_reconnects))
        .filter(models.Call.total_reconnects > 0)
        .scalar()
        or 0
    )
    return schemas.MetricsResponse(
        total_calls=total_calls,
        waiting=waiting,
        in_progress=in_progress,
        ended=ended,
        avg_duration_seconds=float(avg_duration or 0),
        avg_reconnects=float(avg_reconnects or 0),
    )


# -------------------------------------------------------------------
# Señalización WebRTC con Socket.IO
# -------------------------------------------------------------------
rooms = {}  # room_id -> set(sid)


@sio.event
async def connect(sid, environ):
    print("connect:", sid)


@sio.event
async def disconnect(sid):
    print("disconnect:", sid)
    for room_id, members in list(rooms.items()):
        if sid in members:
            members.remove(sid)
            await sio.emit("peer-left", {"sid": sid}, room=room_id, skip_sid=sid)
            if not members:
                rooms.pop(room_id, None)
            break


@sio.event
async def join(sid, data):
    room_id = str(data.get("room"))
    rooms.setdefault(room_id, set()).add(sid)
    await sio.enter_room(sid, room_id)

    peers = [m for m in rooms[room_id] if m != sid]
    await sio.emit("peer-joined", {"sid": sid}, room=room_id, skip_sid=sid)
    return {"ok": True, "peers": peers}


@sio.event
async def relay(sid, data):
    to = data.get("to")
    typ = data.get("type")
    print("relay:", typ, "from", sid, "to", to)

    if not to:
        return

    payload = data.get("payload")
    await sio.emit(
        "signal",
        {"from": sid, "type": typ, "payload": payload},
        to=to,
    )


# -------------------------------------------------------------------
# ASGI App combinada (FastAPI + Socket.IO)
# -------------------------------------------------------------------
socket_app = socketio.ASGIApp(
    sio,
    other_asgi_app=api,   # 👈 IMPORTANTE: usar 'api', no 'app'
    socketio_path="socket.io",  # sin slash inicial/final
)

# Uvicorn usará esta variable
app = socket_app


def bootstrap():
    init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8100,
        proxy_headers=True,
    )

