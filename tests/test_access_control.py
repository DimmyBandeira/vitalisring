"""Sessões, autorização por paciente, consentimento e auditoria."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import api
from models import SessionLocal, init_db, utcnow_naive
from webapp.models_app import AccessLog, CareLink, Consent, Patient, User
from webapp.security.crypto import token_hash
from webapp.security.csrf import validate_csrf
from webapp.security.sessions import COOKIE_NAME, create_session, session_secret


@pytest.fixture
def client():
    with TestClient(api.app) as test_client:
        yield test_client


def make_user_and_patient(role: str, *, consent: bool = False):
    init_db()
    db = SessionLocal()
    suffix = f"{role}-{utcnow_naive().timestamp()}"
    user = User(
        email=f"{suffix}@example.test",
        full_name=f"Usuário {role}",
        role=role,
        is_demo=True,
    )
    grantor = User(
        email=f"grantor-{suffix}@example.test",
        full_name="Responsável de teste",
        role="customer",
        is_demo=True,
    )
    patient = Patient(display_name=f"Paciente {suffix}", is_demo=True)
    unrelated = Patient(display_name=f"Outro {suffix}", is_demo=True)
    db.add_all([user, grantor, patient, unrelated])
    db.flush()
    db.add(CareLink(user_id=user.id, patient_id=patient.id, link_type=role))
    if consent:
        db.add(
            Consent(
                patient_id=patient.id,
                grantor_user_id=grantor.id,
                grantee_user_id=user.id,
            )
        )
    db.commit()
    session = create_session(db, user)
    ids = (user.id, patient.id, unrelated.id, session)
    db.close()
    return ids


def test_session_stores_hashes_instead_of_raw_tokens():
    _user_id, _patient_id, _unrelated_id, new_session = make_user_and_patient("customer")

    assert new_session.record.token_hash != new_session.token
    assert new_session.record.csrf_hash != new_session.csrf_token
    assert new_session.record.token_hash == token_hash(new_session.token, session_secret())


def test_customer_can_access_only_linked_patient(client):
    _user_id, patient_id, unrelated_id, new_session = make_user_and_patient("customer")
    client.cookies.set(COOKIE_NAME, new_session.token)

    allowed = client.get(f"/app/api/patients/{patient_id}/summary")
    denied = client.get(f"/app/api/patients/{unrelated_id}/summary")

    assert allowed.status_code == 200
    assert allowed.json()["patient_id"] == patient_id
    assert denied.status_code == 403


@pytest.mark.parametrize("role", ["doctor", "institution", "technician"])
def test_professional_requires_consent_and_access_is_audited(client, role):
    user_id, patient_id, _unrelated_id, new_session = make_user_and_patient(
        role, consent=False
    )
    client.cookies.set(COOKIE_NAME, new_session.token)

    denied = client.get(f"/app/api/patients/{patient_id}/summary")
    assert denied.status_code == 403

    db = SessionLocal()
    grantor = User(
        email=f"consent-{user_id}@example.test",
        full_name="Responsável do consentimento",
        role="customer",
        is_demo=True,
    )
    db.add(grantor)
    db.flush()
    db.add(
        Consent(
            patient_id=patient_id,
            grantor_user_id=grantor.id,
            grantee_user_id=user_id,
        )
    )
    db.commit()
    db.close()

    allowed = client.get(
        f"/app/api/patients/{patient_id}/summary",
        headers={"X-Request-ID": "test-request-id"},
    )
    assert allowed.status_code == 200

    db = SessionLocal()
    log = (
        db.query(AccessLog)
        .filter(AccessLog.user_id == user_id, AccessLog.patient_id == patient_id)
        .one()
    )
    assert log.action == "view_patient"
    assert log.purpose == "patient_summary"
    assert log.request_id == "test-request-id"
    assert log.ip_hash and "testclient" not in log.ip_hash
    db.close()


def test_revoked_consent_immediately_blocks_professional(client):
    user_id, patient_id, _unrelated_id, new_session = make_user_and_patient(
        "doctor", consent=True
    )
    client.cookies.set(COOKIE_NAME, new_session.token)
    assert client.get(f"/app/api/patients/{patient_id}/summary").status_code == 200

    db = SessionLocal()
    consent = (
        db.query(Consent)
        .filter(Consent.grantee_user_id == user_id, Consent.patient_id == patient_id)
        .one()
    )
    consent.status = "revoked"
    consent.revoked_at = utcnow_naive()
    db.commit()
    db.close()

    assert client.get(f"/app/api/patients/{patient_id}/summary").status_code == 403


def test_expired_session_is_rejected(client):
    _user_id, patient_id, _unrelated_id, new_session = make_user_and_patient("customer")
    db = SessionLocal()
    record = db.get(type(new_session.record), new_session.record.id)
    record.expires_at = utcnow_naive() - timedelta(seconds=1)
    db.commit()
    db.close()
    client.cookies.set(COOKIE_NAME, new_session.token)

    response = client.get(f"/app/api/patients/{patient_id}/summary")

    assert response.status_code == 401


def test_csrf_requires_exact_origin_and_matching_token():
    _user_id, _patient_id, _unrelated_id, new_session = make_user_and_patient("customer")
    arguments = {
        "expected_hash": new_session.record.csrf_hash,
        "allowed_origins": {"https://demo.vitalis.test"},
        "secret": session_secret(),
    }

    assert validate_csrf(
        supplied_token=new_session.csrf_token,
        origin="https://demo.vitalis.test",
        **arguments,
    )
    assert not validate_csrf(
        supplied_token=new_session.csrf_token,
        origin="https://malicioso.test",
        **arguments,
    )
    assert not validate_csrf(
        supplied_token="token-incorreto",
        origin="https://demo.vitalis.test",
        **arguments,
    )
