"""Login forte, recuperação e autorização do console profissional."""

import re

import pyotp
from fastapi.testclient import TestClient

import api
from models import SessionLocal, init_db, utcnow_naive
from webapp.models_app import AccessLog, AppSession, CareLink, Consent, Patient, User
from webapp.security.professional_auth import (
    create_recovery_codes,
    decrypt_totp_secret,
    ensure_totp,
    hash_password,
)
from webapp.security.sessions import COOKIE_NAME, CSRF_COOKIE_NAME, create_session


PASSWORD = "Senha-profissional-123"


def _doctor(email="medica@example.test", role="doctor"):
    init_db()
    db = SessionLocal()
    user = User(email=email, full_name="Dra. Teste", role=role, is_demo=True, password_hash=hash_password(PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    return user_id


def _csrf(response):
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)


def _password_step(client, email="medica@example.test", password=PASSWORD):
    page = client.get("/profissional/login")
    return client.post(
        "/profissional/login",
        data={"email": email, "password": password, "csrf_token": _csrf(page)},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )


def test_wrong_password_does_not_create_session():
    email = "senha-medica@example.test"
    user_id = _doctor(email)
    with TestClient(api.app) as client:
        response = _password_step(client, email=email, password="senha-incorreta")
    assert response.status_code == 200
    assert "Credenciais inválidas" in response.text
    db = SessionLocal()
    assert db.query(AppSession).filter(AppSession.user_id == user_id).count() == 0
    db.close()


def test_first_access_configures_totp_with_local_svg_and_recovery_codes():
    email = "primeiro-acesso@example.test"
    user_id = _doctor(email)
    with TestClient(api.app) as client:
        password = _password_step(client, email=email)
        assert password.status_code == 303
        assert password.headers["location"] == "/profissional/configurar-mfa"
        setup = client.get(password.headers["location"])
        assert setup.status_code == 200
        assert "<svg" in setup.text
        assert "Vitalis Ring" not in setup.text.split("<svg", 1)[1].split("</svg>", 1)[0]
        db = SessionLocal()
        user = db.get(User, user_id)
        secret = decrypt_totp_secret(user.totp_secret_encrypted)
        assert secret and secret not in user.totp_secret_encrypted
        db.close()
        confirmed = client.post(
            "/profissional/configurar-mfa",
            data={"code": pyotp.TOTP(secret).now(), "csrf_token": _csrf(setup)},
            headers={"Origin": "http://testserver"},
        )
        assert confirmed.status_code == 200
        assert "Guarde seus códigos" in confirmed.text
        assert len(re.findall(r"[0-9a-f]{4}-[0-9a-f]{4}", confirmed.text)) == 8
        assert client.cookies.get(COOKIE_NAME)


def test_wrong_totp_does_not_create_session_and_recovery_is_single_use():
    email = "recuperacao@example.test"
    user_id = _doctor(email)
    db = SessionLocal()
    user = db.get(User, user_id)
    ensure_totp(user, db)
    recovery = create_recovery_codes(db, user)[0]
    db.close()
    with TestClient(api.app) as client:
        first = _password_step(client, email=email)
        assert first.headers["location"] == "/profissional/mfa"
        page = client.get("/profissional/mfa")
        wrong = client.post("/profissional/mfa", data={"code": "000000", "csrf_token": _csrf(page)}, headers={"Origin": "http://testserver"})
        assert "Código inválido" in wrong.text
        db = SessionLocal()
        assert db.query(AppSession).filter(AppSession.user_id == user_id).count() == 0
        db.close()
        page = client.get("/profissional/mfa")
        accepted = client.post("/profissional/mfa", data={"code": recovery, "csrf_token": _csrf(page)}, headers={"Origin": "http://testserver"}, follow_redirects=False)
        assert accepted.status_code == 303
        _password_step(client, email=email)
        page = client.get("/profissional/mfa")
        reused = client.post("/profissional/mfa", data={"code": recovery, "csrf_token": _csrf(page)}, headers={"Origin": "http://testserver"})
        assert "Código inválido" in reused.text


def test_technician_second_factor_redirects_to_technical_console():
    email = "tecnico-forte@example.test"
    user_id = _doctor(email, role="technician")
    db = SessionLocal()
    user = db.get(User, user_id)
    ensure_totp(user, db)
    recovery = create_recovery_codes(db, user)[0]
    db.close()
    with TestClient(api.app) as client:
        password = _password_step(client, email=email)
        assert password.headers["location"] == "/profissional/mfa"
        page = client.get("/profissional/mfa")
        accepted = client.post(
            "/profissional/mfa",
            data={"code": recovery, "csrf_token": _csrf(page)},
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
    assert accepted.status_code == 303
    assert accepted.headers["location"] == "/app/tecnico"


def test_first_technician_access_recovery_leads_to_technical_console():
    email = "tecnico-primeiro-acesso@example.test"
    user_id = _doctor(email, role="technician")
    with TestClient(api.app) as client:
        password = _password_step(client, email=email)
        setup = client.get(password.headers["location"])
        db = SessionLocal()
        user = db.get(User, user_id)
        secret = decrypt_totp_secret(user.totp_secret_encrypted)
        db.close()
        confirmed = client.post(
            "/profissional/configurar-mfa",
            data={"code": pyotp.TOTP(secret).now(), "csrf_token": _csrf(setup)},
            headers={"Origin": "http://testserver"},
        )
    assert confirmed.status_code == 200
    assert 'href="/app/tecnico"' in confirmed.text


def test_console_requires_link_and_live_consent_and_audits_view():
    user_id = _doctor("console@example.test")
    db = SessionLocal()
    doctor = db.get(User, user_id)
    allowed = Patient(display_name="Paciente autorizada", is_demo=True)
    revoked = Patient(display_name="Paciente revogada", is_demo=True)
    db.add_all([allowed, revoked])
    db.flush()
    db.add_all([
        CareLink(user_id=doctor.id, patient_id=allowed.id, link_type="doctor"),
        CareLink(user_id=doctor.id, patient_id=revoked.id, link_type="doctor"),
        Consent(patient_id=allowed.id, grantor_user_id=doctor.id, grantee_user_id=doctor.id),
        Consent(patient_id=revoked.id, grantor_user_id=doctor.id, grantee_user_id=doctor.id, status="revoked", revoked_at=utcnow_naive()),
    ])
    db.commit()
    session = create_session(db, doctor)
    allowed_id, revoked_id = allowed.id, revoked.id
    db.close()
    with TestClient(api.app) as client:
        client.cookies.set(COOKIE_NAME, session.token)
        client.cookies.set(CSRF_COOKIE_NAME, session.csrf_token)
        home = client.get("/app/medico")
        assert "Paciente autorizada" in home.text
        assert "Paciente revogada" not in home.text
        detail = client.get(f"/app/medico/pacientes/{allowed_id}")
        assert detail.status_code == 200
        assert client.get(f"/app/medico/pacientes/{revoked_id}").status_code == 403
    db = SessionLocal()
    assert db.query(AccessLog).filter(AccessLog.patient_id == allowed_id, AccessLog.action == "view_patient").count() == 1
    consent = db.query(Consent).filter(Consent.patient_id == allowed_id).one()
    consent.status, consent.revoked_at = "revoked", utcnow_naive()
    db.commit()
    db.close()
    with TestClient(api.app) as client:
        client.cookies.set(COOKIE_NAME, session.token)
        assert client.get(f"/app/medico/pacientes/{allowed_id}").status_code == 403
