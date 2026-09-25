"""Relatório seguro de prontidão para o teste físico da Fase 12."""

import os

from dotenv import load_dotenv
from sqlalchemy import func, inspect


load_dotenv()

from models import Reading, SessionLocal, engine  # noqa: E402
from webapp.models_app import CareLink, Consent, Device, Patient, User  # noqa: E402


def main() -> None:
    keys = (
        "API_KEY",
        "SESSION_SECRET",
        "RING_ADDRESS",
        "API_URL",
        "PUBLIC_BASE_URL",
        "ENV",
        "DEMO_MODE",
        "DEVICE_ID",
        "DATABASE_URL",
        "DB_PATH",
    )
    print("CONFIG")
    for key in keys:
        value = os.getenv(key, "")
        detail = f", length={len(value)}" if key in {"API_KEY", "SESSION_SECRET"} else ""
        print(f"{key}: present={bool(value)}{detail}")
    print("DEVICE_ID_IS_RING01:", os.getenv("DEVICE_ID", "ring-01") == "ring-01")

    if not inspect(engine).has_table("users"):
        print("APP_DATABASE_INITIALIZED:", False)
        print("STRONG_TECHNICIAN_READY:", False)
        print("TECHNICIAN_MFA_CONFIGURED:", False)
        print("RING01_REGISTERED:", False)
        print("RING01_SOURCE_PHYSICAL:", False)
        print("RING01_STATUS: not-registered")
        return

    print("APP_DATABASE_INITIALIZED:", True)
    db = SessionLocal()
    try:
        roles = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())
        print("ROLE_COUNTS:", roles)
        technicians = (
            db.query(User)
            .filter(User.role.in_(("technician", "owner")), User.is_active.is_(True))
            .all()
        )
        strong = [user for user in technicians if user.password_hash]
        print("STRONG_TECHNICIAN_READY:", bool(strong))
        print("TECHNICIAN_MFA_CONFIGURED:", any(user.totp_secret_encrypted for user in strong))
        doctors = db.query(User).filter(User.role == "doctor", User.is_active.is_(True)).all()
        print("STRONG_DOCTOR_READY:", any(user.password_hash for user in doctors))
        print("PATIENT_COUNT:", db.query(Patient).count())
        print("ACTIVE_CARE_LINK_COUNT:", db.query(CareLink).filter(CareLink.is_active.is_(True)).count())
        print("ACTIVE_CONSENT_COUNT:", db.query(Consent).filter(Consent.status == "active").count())
        devices = db.query(Device).order_by(Device.created_at.asc()).all()
        print(
            "DEVICE_STATES:",
            [
                {"device_id": device.device_id, "source": device.source, "status": device.status}
                for device in devices
            ],
        )
        ring = db.query(Device).filter(Device.device_id == "ring-01").first()
        print("RING01_REGISTERED:", bool(ring))
        print("RING01_SOURCE_PHYSICAL:", bool(ring and ring.source == "physical"))
        print("RING01_STATUS:", ring.status if ring else "not-registered")
        readings = db.query(Reading).filter(Reading.device_id == "ring-01")
        latest = readings.order_by(Reading.timestamp.desc()).first()
        reading_types = sorted({kind for (kind,) in readings.with_entities(Reading.type).distinct().all()})
        print("RING01_READING_COUNT:", readings.count())
        print("RING01_READING_TYPES:", reading_types)
        print("RING01_LATEST_READING_AT:", latest.timestamp.isoformat() if latest else "none")
    finally:
        db.close()


if __name__ == "__main__":
    main()
