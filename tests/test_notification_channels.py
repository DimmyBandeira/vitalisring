"""Seleção, consentimento e idempotência dos canais de aviso."""

import logging

from models import SessionLocal, init_db, utcnow_naive
from webapp.alerts.channels import dispatch_notification
from webapp.models_app import NotificationAttempt, NotificationPreference, Patient, User


class FakeNotifier:
    def __init__(self, sent):
        self.sent = sent

    def send(self, notification):
        self.sent.append(notification)


def _records(*, opted_in=True, verified=True):
    init_db()
    db = SessionLocal()
    suffix = str(utcnow_naive().timestamp())
    user = User(email=f"notify-{suffix}@example.test", full_name="Familiar", role="customer", is_demo=True)
    patient = Patient(display_name="Maria", is_demo=True)
    db.add_all([user, patient])
    db.flush()
    preference = NotificationPreference(user_id=user.id, patient_id=patient.id, channel="whatsapp", destination="5511999999999", opted_in=opted_in, verified_at=utcnow_naive() if verified else None)
    db.add(preference)
    db.commit()
    return db, user.id, patient.id


def test_without_opt_in_or_verification_no_channel_is_called():
    for opted_in, verified in [(False, True), (True, False)]:
        db, user_id, patient_id = _records(opted_in=opted_in, verified=verified)
        called = []
        result = dispatch_notification(db, patient_id=patient_id, user_id=user_id, event_key=f"no-{opted_in}-{verified}", patient_name="Maria", level="warn", notifier_factory=lambda _channel: FakeNotifier(called))
        assert result == [] and called == []
        db.close()


def test_channel_selection_and_retry_are_idempotent(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_SEND_ENABLED", "1")
    db, user_id, patient_id = _records()
    sent = []
    factory_calls = []

    def factory(channel):
        factory_calls.append(channel)
        return FakeNotifier(sent)

    first = dispatch_notification(db, patient_id=patient_id, user_id=user_id, event_key="alert-123", patient_name="Maria", level="critical", notifier_factory=factory)
    second = dispatch_notification(db, patient_id=patient_id, user_id=user_id, event_key="alert-123", patient_name="Maria", level="critical", notifier_factory=factory)
    assert factory_calls == ["whatsapp"]
    assert len(sent) == 1
    assert first[0].id == second[0].id
    assert db.query(NotificationAttempt).count() == 1
    assert "192" in sent[0].body and "critical" not in sent[0].body
    db.close()


def test_default_mode_is_preview_only_and_logs_no_content(monkeypatch, caplog):
    monkeypatch.setenv("NOTIFICATION_SEND_ENABLED", "0")
    db, user_id, patient_id = _records()
    with caplog.at_level(logging.INFO, logger="vitalis.notifications"):
        result = dispatch_notification(db, patient_id=patient_id, user_id=user_id, event_key="preview-1", patient_name="Nome Sigiloso", level="alert")
    assert result[0].status == "preview"
    assert "Nome Sigiloso" not in caplog.text
    assert "5511999999999" not in caplog.text
    assert "alert-1" not in caplog.text
    db.close()
