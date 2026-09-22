"""Canais de aviso opt-in, idempotentes e desligados por padrão."""

import logging
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from webapp.alerts.rules import message_preview
from webapp.models_app import NotificationAttempt, NotificationPreference
from webapp.security.config import env_flag

logger = logging.getLogger("vitalis.notifications")


@dataclass(frozen=True)
class Notification:
    destination: str
    subject: str
    body: str


class Notifier(Protocol):
    def send(self, notification: Notification) -> None: ...


class ConsoleNotifier:
    def send(self, notification: Notification) -> None:
        logger.info("notification channel=console status=preview")


class SMTPNotifier:
    def send(self, notification: Notification) -> None:
        message = EmailMessage()
        message["Subject"], message["From"], message["To"] = notification.subject, os.environ["MAIL_FROM"], notification.destination
        message.set_content(notification.body)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=15) as smtp:
            smtp.starttls()
            if os.environ.get("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(message)


class WhatsAppNotifier:
    def send(self, notification: Notification) -> None:
        url = f"https://graph.facebook.com/v22.0/{os.environ['WHATSAPP_PHONE_ID']}/messages"
        response = httpx.post(url, headers={"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"}, json={"messaging_product": "whatsapp", "to": notification.destination, "type": "text", "text": {"body": notification.body}}, timeout=15)
        response.raise_for_status()


def configured_notifier(channel: str) -> Notifier | None:
    if not env_flag("NOTIFICATION_SEND_ENABLED"):
        return ConsoleNotifier()
    if channel == "email" and os.environ.get("SMTP_HOST") and os.environ.get("MAIL_FROM"):
        return SMTPNotifier()
    if channel == "whatsapp" and os.environ.get("WHATSAPP_TOKEN") and os.environ.get("WHATSAPP_PHONE_ID"):
        return WhatsAppNotifier()
    return None


def dispatch_notification(db: Session, *, patient_id: str, user_id: str, event_key: str, patient_name: str, level: str, notifier_factory=configured_notifier) -> list[NotificationAttempt]:
    attempts = []
    preferences = db.query(NotificationPreference).filter(NotificationPreference.patient_id == patient_id, NotificationPreference.user_id == user_id, NotificationPreference.opted_in.is_(True), NotificationPreference.verified_at.is_not(None)).all()
    preview = message_preview(patient_name, level)
    for preference in preferences:
        key = f"{event_key}:{user_id}:{preference.channel}"
        existing = db.query(NotificationAttempt).filter(NotificationAttempt.idempotency_key == key).first()
        if existing:
            attempts.append(existing)
            continue
        notifier = notifier_factory(preference.channel)
        attempt = NotificationAttempt(idempotency_key=key, patient_id=patient_id, user_id=user_id, channel=preference.channel, status="skipped" if notifier is None else "prepared")
        db.add(attempt)
        db.commit()
        if notifier:
            try:
                body = preview["whatsapp"] if preference.channel == "whatsapp" else preview["email_body"]
                notifier.send(Notification(preference.destination, preview["email_subject"], body))
                attempt.status = "sent" if env_flag("NOTIFICATION_SEND_ENABLED") else "preview"
            except Exception as exc:
                attempt.status, attempt.error_code = "failed", type(exc).__name__
            db.commit()
        logger.info("notification channel=%s status=%s", preference.channel, attempt.status)
        attempts.append(attempt)
    return attempts
