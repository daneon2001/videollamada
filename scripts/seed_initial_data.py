import os

from app.db import SessionLocal, init_db
from app import models
from app.security import get_password_hash


def upsert_user(session, *, email: str, name: str, password: str, role: models.UserRole):
    email = email.lower().strip()
    user = session.query(models.User).filter_by(email=email).first()
    if user:
        print(f"[seed] Usuario existente: {email} ({user.role.value})")
        return user

    user = models.User(
        email=email,
        full_name=name,
        role=role,
        password_hash=get_password_hash(password),
        is_available=(role == models.UserRole.doctor),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"[seed] Usuario creado: {email} ({role.value})")
    return user


def main():
    init_db()

    defaults = {
        "doctor": {
            "email": os.getenv("DEFAULT_DOCTOR_EMAIL", "doctor@example.com"),
            "password": os.getenv("DEFAULT_DOCTOR_PASSWORD", "Doctor123!"),
            "name": os.getenv("DEFAULT_DOCTOR_NAME", "Dr. Default"),
        },
        "patient": {
            "email": os.getenv("DEFAULT_PATIENT_EMAIL", "patient@example.com"),
            "password": os.getenv("DEFAULT_PATIENT_PASSWORD", "Patient123!"),
            "name": os.getenv("DEFAULT_PATIENT_NAME", "Paciente Demo"),
        },
    }

    with SessionLocal() as session:
        upsert_user(
            session,
            email=defaults["doctor"]["email"],
            name=defaults["doctor"]["name"],
            password=defaults["doctor"]["password"],
            role=models.UserRole.doctor,
        )
        upsert_user(
            session,
            email=defaults["patient"]["email"],
            name=defaults["patient"]["name"],
            password=defaults["patient"]["password"],
            role=models.UserRole.patient,
        )


if __name__ == "__main__":
    main()
