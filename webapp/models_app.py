"""Modelos aditivos da área logada; a tabela legada ``readings`` não muda."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from models import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_id)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    totp_secret = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class LoginToken(Base):
    __tablename__ = "login_tokens"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    code_hash = Column(String, index=True, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AppSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    csrf_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)
    absolute_expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=new_id)
    display_name = Column(String, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True, default=new_id)
    device_id = Column(String, unique=True, index=True, nullable=False)
    serial_number = Column(String, unique=True, index=True, nullable=True)
    patient_id = Column(String, ForeignKey("patients.id"), unique=True, index=True, nullable=True)
    source = Column(String, default="physical", nullable=False)
    status = Column(String, default="pending", index=True, nullable=False)
    registered_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)


class CareLink(Base):
    __tablename__ = "care_links"
    __table_args__ = (
        UniqueConstraint("user_id", "patient_id", "link_type", name="uq_care_link"),
    )

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.id"), index=True, nullable=False)
    link_type = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    starts_at = Column(DateTime, default=utcnow, nullable=False)
    ends_at = Column(DateTime, nullable=True)


class Consent(Base):
    __tablename__ = "consents"

    id = Column(String, primary_key=True, default=new_id)
    patient_id = Column(String, ForeignKey("patients.id"), index=True, nullable=False)
    grantor_user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    grantee_user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    scope = Column(String, default="view", nullable=False)
    status = Column(String, default="active", index=True, nullable=False)
    granted_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=new_id)
    patient_id = Column(String, ForeignKey("patients.id"), index=True, nullable=False)
    device_id = Column(String, ForeignKey("devices.id"), index=True, nullable=True)
    level = Column(String, index=True, nullable=False)
    rule_key = Column(String, nullable=False)
    status = Column(String, default="open", nullable=False)
    is_demo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)


class AccessLog(Base):
    __tablename__ = "access_log"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.id"), index=True, nullable=True)
    action = Column(String, index=True, nullable=False)
    purpose = Column(String, nullable=False)
    request_id = Column(String, index=True, nullable=True)
    ip_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True, nullable=False)


class RefreshRequest(Base):
    __tablename__ = "refresh_requests"

    id = Column(String, primary_key=True, default=new_id)
    patient_id = Column(String, ForeignKey("patients.id"), index=True, nullable=False)
    device_id = Column(String, ForeignKey("devices.id"), index=True, nullable=False)
    requested_by = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    status = Column(String, default="pending", index=True, nullable=False)
    requested_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
