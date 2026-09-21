"""Painel familiar, isolamento de paciente e atualização sintética."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api
from models import Reading, SessionLocal, init_db, utcnow_naive
from webapp.models_app import AccessLog, Alert, CareLink, Consent, Device, Patient, RefreshRequest, User
from webapp.security.sessions import COOKIE_NAME, CSRF_COOKIE_NAME, create_session
from webapp.services.family_dashboard import local_datetime


@pytest.fixture
def family_context():
    init_db()
    db = SessionLocal()
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    user = User(
        email=f"family-{suffix}@example.test",
        full_name="Família Teste",
        role="customer",
        is_demo=True,
        consent_version="test",
        consented_at=utcnow_naive(),
    )
    patient = Patient(display_name="Maria Teste", is_demo=True)
    other = Patient(display_name="Paciente sem vínculo", is_demo=True)
    doctor = User(
        email=f"doctor-{suffix}@example.test",
        full_name="Dra. Acompanhante",
        role="doctor",
        is_demo=True,
    )
    db.add_all([user, patient, other, doctor])
    db.flush()
    device = Device(
        device_id=f"demo-family-{suffix}",
        patient_id=patient.id,
        source="synthetic",
        status="active",
    )
    db.add(device)
    db.add(CareLink(user_id=user.id, patient_id=patient.id, link_type="guardian"))
    db.add(CareLink(user_id=doctor.id, patient_id=patient.id, link_type="doctor"))
    now = utcnow_naive()
    db.add_all(
        [
            Reading(device_id=device.device_id, type="heart_rate", value=71, timestamp=now),
            Reading(device_id=device.device_id, type="spo2", value=98, timestamp=now),
            Reading(device_id=device.device_id, type="battery", value=83, timestamp=now),
        ]
    )
    db.commit()
    session = create_session(db, user)
    result = {
        "patient_id": patient.id,
        "other_id": other.id,
        "device_id": device.device_id,
        "device_pk": device.id,
        "recipient_id": doctor.id,
        "token": session.token,
        "csrf": session.csrf_token,
    }
    db.close()
    return result


@pytest.fixture
def client(family_context):
    with TestClient(api.app) as test_client:
        test_client.cookies.set(COOKIE_NAME, family_context["token"])
        test_client.cookies.set(CSRF_COOKIE_NAME, family_context["csrf"])
        yield test_client


def test_family_dashboard_is_calm_labeled_and_details_are_collapsed(client):
    response = client.get("/app")

    assert response.status_code == 200
    assert "Tudo em ordem" in response.text
    assert "Dados fictícios — demonstração" in response.text
    assert "Última comunicação" in response.text
    assert "Ver detalhes das estimativas" in response.text
    assert "Frequência cardíaca" in response.text
    assert "Quem recebe avisos" in response.text
    assert "Dra. Acompanhante" in response.text
    assert "Autorizar" in response.text
    assert "Simulador da demonstração ativo" in response.text


def test_sao_paulo_conversion_keeps_database_utc_naive():
    value = datetime(2026, 9, 21, 15, 0, 0)
    converted = local_datetime(value)

    assert converted.tzinfo is not None
    assert converted.hour == 12
    assert converted.utcoffset().total_seconds() == -3 * 3600


def test_refresh_updates_linked_demo_patient_and_records_request(client, family_context):
    before_db = SessionLocal()
    before = before_db.query(Reading).filter(Reading.device_id == family_context["device_id"]).count()
    before_db.close()
    response = client.post(
        f"/app/pacientes/{family_context['patient_id']}/atualizar",
        data={"csrf_token": family_context["csrf"]},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    db = SessionLocal()
    request = db.query(RefreshRequest).filter(RefreshRequest.patient_id == family_context["patient_id"]).one()
    after = db.query(Reading).filter(Reading.device_id == family_context["device_id"]).count()
    assert request.status == "completed"
    assert request.completed_at is not None
    assert after == before + 3
    db.close()


def test_refresh_rejects_patient_id_tampering(client, family_context):
    response = client.post(
        f"/app/pacientes/{family_context['other_id']}/atualizar",
        data={"csrf_token": family_context["csrf"]},
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("level", "label"),
    [
        ("info", "Para saber"),
        ("warn", "Vale observar"),
        ("alert", "Importante"),
        ("critical", "Precisa de você agora"),
    ],
)
def test_open_alert_drives_the_five_level_card(client, family_context, level, label):
    db = SessionLocal()
    db.add(
        Alert(
            patient_id=family_context["patient_id"],
            device_id=family_context["device_pk"],
            level=level,
            rule_key="browser-test",
            is_demo=True,
        )
    )
    db.commit()
    db.close()

    response = client.get("/app")

    assert response.status_code == 200
    assert label in response.text


def test_customer_can_authorize_and_revoke_linked_recipient(client, family_context):
    url = (
        f"/app/pacientes/{family_context['patient_id']}"
        f"/destinatarios/{family_context['recipient_id']}"
    )
    authorized = client.post(
        url,
        data={"csrf_token": family_context["csrf"], "enabled": "yes"},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    assert authorized.status_code == 303

    db = SessionLocal()
    consent = (
        db.query(Consent)
        .filter(Consent.grantee_user_id == family_context["recipient_id"])
        .one()
    )
    assert consent.status == "active"
    assert consent.revoked_at is None
    db.close()

    revoked = client.post(
        url,
        data={"csrf_token": family_context["csrf"], "enabled": "no"},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    assert revoked.status_code == 303

    db = SessionLocal()
    consent = (
        db.query(Consent)
        .filter(Consent.grantee_user_id == family_context["recipient_id"])
        .one()
    )
    actions = [
        item.action
        for item in db.query(AccessLog)
        .filter(AccessLog.patient_id == family_context["patient_id"])
        .all()
    ]
    assert consent.status == "revoked"
    assert consent.revoked_at is not None
    assert actions == ["alert_recipient_enabled", "alert_recipient_disabled"]
    db.close()
