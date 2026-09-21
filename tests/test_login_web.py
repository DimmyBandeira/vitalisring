"""Fluxo web B2C: login, consentimento, sessão e logout."""

import re
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

import api
from models import SessionLocal, init_db, utcnow_naive
from webapp.models_app import AppSession, User
from webapp.security.sessions import COOKIE_NAME, CSRF_COOKIE_NAME, secure_cookie_enabled


@pytest.fixture
def client():
    with TestClient(api.app) as test_client:
        yield test_client


def create_customer(*, is_demo: bool) -> User:
    init_db()
    db = SessionLocal()
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    user = User(
        email=f"web-{suffix}@example.test",
        full_name="Maria Demonstração" if is_demo else "Cliente Real",
        role="customer",
        is_demo=is_demo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.expunge(user)
    db.close()
    return user


def get_login_csrf(client: TestClient, path: str = "/login") -> str:
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def request_access(client: TestClient, user: User):
    csrf = get_login_csrf(client)
    return client.post(
        "/login",
        data={"email": user.email, "csrf_token": csrf},
        headers={"Origin": "http://testserver"},
    )


def test_demo_magic_link_consent_and_logout_flow(client):
    user = create_customer(is_demo=True)
    requested = request_access(client, user)

    assert requested.status_code == 200
    assert "Modo demonstração — link de acesso" in requested.text
    link_match = re.search(r'href="(http://testserver/login/token\?token=[^"]+)"', requested.text)
    assert link_match
    magic_path = urlsplit(link_match.group(1)).path + "?" + urlsplit(link_match.group(1)).query

    authenticated = client.get(magic_path, follow_redirects=False)
    assert authenticated.status_code == 303
    assert authenticated.headers["location"] == "/app/consentimento"
    set_cookies = authenticated.headers.get_list("set-cookie")
    session_cookie = next(value for value in set_cookies if value.startswith(f"{COOKIE_NAME}="))
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Secure" not in session_cookie

    consent_page = client.get("/app/consentimento")
    assert consent_page.status_code == 200
    csrf = client.cookies.get(CSRF_COOKIE_NAME)
    accepted = client.post(
        "/app/consentimento",
        data={"accepted": "yes", "csrf_token": csrf},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    assert accepted.status_code == 303
    assert accepted.headers["location"] == "/app"

    app_home = client.get("/app")
    assert app_home.status_code == 200
    assert "Olá, Maria Demonstração" in app_home.text
    assert "Dados fictícios — demonstração" in app_home.text

    logout_page = client.get("/logout")
    assert logout_page.status_code == 200
    logged_out = client.post(
        "/logout",
        data={"csrf_token": csrf},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    assert logged_out.status_code == 303
    assert client.get("/app", follow_redirects=False).headers["location"] == "/login"

    db = SessionLocal()
    assert db.query(AppSession).filter(AppSession.user_id == user.id).one().revoked_at is not None
    db.close()


def test_magic_link_cannot_be_reused(client):
    user = create_customer(is_demo=True)
    requested = request_access(client, user)
    link = re.search(r'href="(http://testserver/login/token\?token=[^"]+)"', requested.text).group(1)
    parts = urlsplit(link)
    path = parts.path + "?" + parts.query

    assert client.get(path, follow_redirects=False).headers["location"] == "/app/consentimento"
    with TestClient(api.app) as second_client:
        reused = second_client.get(path, follow_redirects=False)
    assert reused.status_code == 303
    assert reused.headers["location"] == "/login?erro=link-invalido"


def test_login_response_is_neutral_for_real_and_unknown_email(client):
    real_user = create_customer(is_demo=False)
    real_response = request_access(client, real_user)
    csrf = get_login_csrf(client)
    unknown_response = client.post(
        "/login",
        data={"email": "desconhecido@example.test", "csrf_token": csrf},
        headers={"Origin": "http://testserver"},
    )

    assert real_response.status_code == unknown_response.status_code == 200
    assert real_response.text == unknown_response.text
    assert "Modo demonstração" not in real_response.text


def test_login_post_rejects_missing_or_foreign_csrf(client):
    user = create_customer(is_demo=True)
    get_login_csrf(client)

    missing = client.post(
        "/login",
        data={"email": user.email},
        headers={"Origin": "http://testserver"},
    )
    foreign = client.post(
        "/login",
        data={"email": user.email, "csrf_token": "invalid"},
        headers={"Origin": "https://malicioso.test"},
    )

    assert missing.status_code == 403
    assert foreign.status_code == 403


def test_six_digit_code_works_in_another_browser_flow(client):
    user = create_customer(is_demo=True)
    requested = request_access(client, user)
    code = re.search(r'class="demo-code">(\d{6})</strong>', requested.text).group(1)
    csrf = get_login_csrf(client, "/login/codigo")

    response = client.post(
        "/login/codigo",
        data={"email": user.email, "code": code, "csrf_token": csrf},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/app/consentimento"


def test_secure_cookie_policy(monkeypatch):
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.vitalis.test")
    assert secure_cookie_enabled()

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    assert not secure_cookie_enabled()

    monkeypatch.setenv("PUBLIC_BASE_URL", "https://dev.vitalis.test")
    assert secure_cookie_enabled()
