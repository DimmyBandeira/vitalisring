"""Auditoria mínima sem valores de sinais vitais."""

import hashlib

from sqlalchemy.orm import Session

from webapp.models_app import AccessLog, User


AUDITED_ROLES = {"doctor", "institution", "technician"}


def anonymize_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def record_patient_access(
    db: Session,
    *,
    user: User,
    patient_id: str,
    purpose: str,
    request_id: str | None,
    ip: str | None,
) -> None:
    if user.role not in AUDITED_ROLES:
        return
    record_action(
        db,
        user=user,
        patient_id=patient_id,
        action="view_patient",
        purpose=purpose,
        request_id=request_id,
        ip=ip,
    )


def record_action(
    db: Session,
    *,
    user: User,
    patient_id: str | None,
    action: str,
    purpose: str,
    request_id: str | None,
    ip: str | None,
) -> None:
    db.add(
        AccessLog(
            user_id=user.id,
            patient_id=patient_id,
            action=action,
            purpose=purpose,
            request_id=request_id,
            ip_hash=anonymize_ip(ip),
        )
    )
    db.commit()
