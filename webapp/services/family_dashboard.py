"""Leitura segura dos dados necessários ao painel familiar."""

import json
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models import Reading, utcnow_naive
from webapp.models_app import Alert, CareLink, Consent, Device, Patient, User


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
RING_STATUS_PATH = Path("ring_status.json")
STATUS_PRESENTATION = {
    "ok": ("Tudo em ordem", "✓", "Nenhum aviso novo no momento."),
    "info": ("Para saber", "i", "Há uma informação nova para você."),
    "warn": ("Vale observar", "!", "Vale acompanhar esta informação no app."),
    "alert": ("Importante", "!", "Há uma informação importante para você."),
    "critical": (
        "Precisa de você agora",
        "!",
        "Abra os detalhes agora. Em emergência, ligue 192.",
    ),
}


@dataclass(frozen=True)
class DashboardState:
    patient: Patient
    device: Device | None
    status_key: str
    status_label: str
    status_icon: str
    status_message: str
    latest_at: object | None
    latest_relative: str
    latest_values: dict[str, Reading]
    alerts: list[Alert]
    recipients: list[dict]
    ring_connected: bool | None


def local_datetime(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(SAO_PAULO)


def relative_time(value) -> str:
    if value is None:
        return "ainda sem leitura"
    seconds = max(0, int((utcnow_naive() - value).total_seconds()))
    if seconds < 60:
        return "agora"
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} h"
    return f"há {hours // 24} d"


def _ring_connected(device: Device | None) -> bool | None:
    if device is None or device.source == "synthetic":
        return None
    try:
        payload = json.loads(RING_STATUS_PATH.read_text(encoding="utf-8"))
        return bool(payload.get("connected"))
    except (OSError, ValueError, TypeError):
        return False


def load_family_dashboard(db: Session, user: User) -> DashboardState | None:
    now = utcnow_naive()
    link = (
        db.query(CareLink)
        .filter(
            CareLink.user_id == user.id,
            CareLink.is_active.is_(True),
            CareLink.starts_at <= now,
        )
        .order_by(CareLink.starts_at.asc())
        .first()
    )
    if link is None or (link.ends_at and link.ends_at <= now):
        return None
    patient = db.get(Patient, link.patient_id)
    device = db.query(Device).filter(Device.patient_id == patient.id).first()
    latest_values = {}
    latest_at = None
    if device:
        for reading_type in ("heart_rate", "spo2", "battery"):
            reading = (
                db.query(Reading)
                .filter(Reading.device_id == device.device_id, Reading.type == reading_type)
                .order_by(Reading.timestamp.desc())
                .first()
            )
            if reading:
                latest_values[reading_type] = reading
                if latest_at is None or reading.timestamp > latest_at:
                    latest_at = reading.timestamp

    alerts = (
        db.query(Alert)
        .filter(Alert.patient_id == patient.id)
        .order_by(Alert.created_at.desc())
        .limit(10)
        .all()
    )
    open_alert = next(
        (alert for alert in alerts if alert.status == "open" and alert.level in STATUS_PRESENTATION),
        None,
    )
    if open_alert:
        status_key = open_alert.level
        status_label, status_icon, status_message = STATUS_PRESENTATION[status_key]
    elif latest_at and latest_at >= now - timedelta(minutes=15):
        status_key = "ok"
        status_label, status_icon, _message = STATUS_PRESENTATION[status_key]
        status_message = "O dispositivo se comunicou recentemente."
    else:
        status_key = "info"
        status_label, status_icon, _message = STATUS_PRESENTATION[status_key]
        status_message = "Ainda não recebemos uma leitura recente do dispositivo."
    recipient_links = (
        db.query(CareLink)
        .filter(CareLink.patient_id == patient.id, CareLink.is_active.is_(True))
        .all()
    )
    recipients = []
    for recipient_link in recipient_links:
        recipient = db.get(User, recipient_link.user_id)
        if recipient is None:
            continue
        consent = (
            db.query(Consent)
            .filter(
                Consent.patient_id == patient.id,
                Consent.grantee_user_id == recipient.id,
                Consent.status == "active",
                Consent.revoked_at.is_(None),
            )
            .first()
        )
        recipients.append(
            {
                "id": recipient.id,
                "name": recipient.full_name,
                "relationship": recipient_link.link_type,
                "authorized": recipient.role == "customer" or consent is not None,
            }
        )

    return DashboardState(
        patient=patient,
        device=device,
        status_key=status_key,
        status_label=status_label,
        status_icon=status_icon,
        status_message=status_message,
        latest_at=local_datetime(latest_at),
        latest_relative=relative_time(latest_at),
        latest_values=latest_values,
        alerts=alerts,
        recipients=recipients,
        ring_connected=_ring_connected(device),
    )
