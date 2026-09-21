"""Fluxo técnico de cadastro e ativação com dispositivo sintético."""

import re
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

import api
from models import Reading, SessionLocal, init_db, utcnow_naive
from webapp.models_app import CareLink, Device, Patient, User
from webapp.security.sessions import COOKIE_NAME, CSRF_COOKIE_NAME, create_session


def create_user(role: str, *, is_demo: bool = True):
    init_db()
    db = SessionLocal()
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    user = User(
        email=f"{role}-{suffix}@example.test",
        full_name=f"Usuário {role}",
        role=role,
        is_demo=is_demo,
        consented_at=utcnow_naive() if role == "customer" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    session = create_session(db, user)
    user_id = user.id
    email = user.email
    db.close()
    return user_id, email, session


@pytest.fixture
def technician_client():
    user_id, email, session = create_user("technician")
    with TestClient(api.app) as client:
        client.cookies.set(COOKIE_NAME, session.token)
        client.cookies.set(CSRF_COOKIE_NAME, session.csrf_token)
        yield client, user_id, email, session.csrf_token


def onboarding_payload(csrf_token: str, suffix: str):
    return {
        "customer_name": "Ana Responsável",
        "customer_email": f"ana-{suffix}@example.test",
        "patient_name": "Maria Monitorada",
        "device_id": f"demo-{suffix}",
        "serial_number": f"SYN-{suffix}",
        "source": "synthetic",
        "csrf_token": csrf_token,
    }


def test_demo_technician_can_login_and_is_redirected_to_technical_area():
    init_db()
    db = SessionLocal()
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    technician = User(
        email=f"tech-login-{suffix}@example.test",
        full_name="Técnico Demo",
        role="technician",
        is_demo=True,
    )
    db.add(technician)
    db.commit()
    technician_email = technician.email
    db.close()

    with TestClient(api.app) as client:
        page = client.get("/login")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        requested = client.post(
            "/login",
            data={"email": technician_email, "csrf_token": csrf},
            headers={"Origin": "http://testserver"},
        )
        link = re.search(r'href="(http://testserver/login/token\?token=[^"]+)"', requested.text).group(1)
        parts = urlsplit(link)
        response = client.get(parts.path + "?" + parts.query, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/app/tecnico"


def test_technician_creates_customer_patient_device_and_invite_atomically(technician_client):
    client, technician_id, _email, csrf = technician_client
    suffix = str(utcnow_naive().timestamp()).replace(".", "")

    response = client.post(
        "/app/tecnico/novo",
        data=onboarding_payload(csrf, suffix),
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 201
    assert "Implantação criada" in response.text
    assert "Dados fictícios — demonstração" in response.text
    assert "Convite de demonstração" in response.text
    db = SessionLocal()
    customer = db.query(User).filter(User.email == f"ana-{suffix}@example.test").one()
    patient = db.query(Patient).filter(Patient.display_name == "Maria Monitorada").order_by(Patient.created_at.desc()).first()
    device = db.query(Device).filter(Device.device_id == f"demo-{suffix}").one()
    link = db.query(CareLink).filter(CareLink.user_id == customer.id, CareLink.patient_id == patient.id).one()
    assert customer.role == "customer"
    assert customer.is_demo and patient.is_demo
    assert device.patient_id == patient.id
    assert device.registered_by == technician_id
    assert link.link_type == "guardian"
    db.close()


def test_duplicate_failure_does_not_create_partial_second_registration(technician_client):
    client, _technician_id, _email, csrf = technician_client
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    payload = onboarding_payload(csrf, suffix)
    assert client.post("/app/tecnico/novo", data=payload, headers={"Origin": "http://testserver"}).status_code == 201

    db = SessionLocal()
    before = (db.query(User).count(), db.query(Patient).count(), db.query(Device).count())
    db.close()
    duplicate = client.post(
        "/app/tecnico/novo",
        data={**payload, "patient_name": "Cadastro que não deve existir"},
        headers={"Origin": "http://testserver"},
    )
    db = SessionLocal()
    after = (db.query(User).count(), db.query(Patient).count(), db.query(Device).count())
    db.close()

    assert duplicate.status_code == 409
    assert before == after


def test_synthetic_first_reading_activates_only_the_registered_device(technician_client):
    client, _technician_id, _email, csrf = technician_client
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    payload = onboarding_payload(csrf, suffix)
    assert client.post("/app/tecnico/novo", data=payload, headers={"Origin": "http://testserver"}).status_code == 201
    db = SessionLocal()
    device = db.query(Device).filter(Device.device_id == payload["device_id"]).one()
    device_pk = device.id
    db.close()

    activated = client.post(
        f"/app/tecnico/dispositivos/{device_pk}/ativar-demo",
        data={"csrf_token": csrf},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )

    assert activated.status_code == 303
    db = SessionLocal()
    device = db.get(Device, device_pk)
    readings = db.query(Reading).filter(Reading.device_id == payload["device_id"]).all()
    assert device.status == "active"
    assert device.activated_at is not None
    assert {reading.type for reading in readings} == {"heart_rate", "spo2", "battery"}
    db.close()


def test_customer_cannot_open_technical_area():
    _user_id, _email, session = create_user("customer")
    with TestClient(api.app) as client:
        client.cookies.set(COOKIE_NAME, session.token)
        response = client.get("/app/tecnico")

    assert response.status_code == 403
