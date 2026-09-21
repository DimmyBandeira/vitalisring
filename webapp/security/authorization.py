"""Política central de acesso a pacientes."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import utcnow_naive
from webapp.models_app import CareLink, Consent, Patient, User


PROFESSIONAL_ROLES = {"doctor", "institution", "technician"}


def _active_link(db: Session, user_id: str, patient_id: str, now: datetime) -> CareLink | None:
    return (
        db.query(CareLink)
        .filter(
            CareLink.user_id == user_id,
            CareLink.patient_id == patient_id,
            CareLink.is_active.is_(True),
            CareLink.starts_at <= now,
            or_(CareLink.ends_at.is_(None), CareLink.ends_at > now),
        )
        .first()
    )


def _active_consent(db: Session, user_id: str, patient_id: str, now: datetime) -> Consent | None:
    return (
        db.query(Consent)
        .filter(
            Consent.grantee_user_id == user_id,
            Consent.patient_id == patient_id,
            Consent.status == "active",
            Consent.revoked_at.is_(None),
            or_(Consent.expires_at.is_(None), Consent.expires_at > now),
        )
        .first()
    )


def authorize_patient(db: Session, user: User, patient_id: str) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    if user.role == "owner":
        return patient

    now = utcnow_naive()
    if _active_link(db, user.id, patient_id, now) is None:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    if user.role in PROFESSIONAL_ROLES and _active_consent(db, user.id, patient_id, now) is None:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    return patient
