"""Proteção CSRF por token de sessão e comparação exata de origem."""

import os
from urllib.parse import urlsplit

from fastapi import Request

from webapp.security.crypto import constant_time_equal, new_token, token_hash
from webapp.security.sessions import session_secret


LOGIN_CSRF_COOKIE = "vr_login_csrf"
LOCAL_ORIGINS = {"http://localhost:8000", "http://127.0.0.1:8000"}


def normalized_origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("origem inválida")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def validate_csrf(
    *,
    supplied_token: str | None,
    expected_hash: str,
    origin: str | None,
    allowed_origins: set[str],
    secret: str,
) -> bool:
    if not supplied_token or not origin:
        return False
    try:
        request_origin = normalized_origin(origin)
        normalized_allowed = {normalized_origin(item) for item in allowed_origins}
    except ValueError:
        return False
    if request_origin not in normalized_allowed:
        return False
    supplied_hash = token_hash(supplied_token, secret)
    return constant_time_equal(supplied_hash, expected_hash)


def issue_login_csrf() -> tuple[str, str]:
    raw_token = new_token()
    return raw_token, token_hash(raw_token, session_secret())


def configured_origins() -> set[str]:
    origins = {os.environ.get("PUBLIC_BASE_URL", "")}
    if os.environ.get("ENV", "dev").strip().lower() in {"dev", "test"}:
        origins.update(LOCAL_ORIGINS)
    return origins


def validate_login_csrf(request: Request, supplied_token: str | None) -> bool:
    expected_hash = request.cookies.get(LOGIN_CSRF_COOKIE, "")
    return bool(expected_hash) and validate_csrf(
        supplied_token=supplied_token,
        expected_hash=expected_hash,
        origin=request.headers.get("Origin"),
        allowed_origins=configured_origins(),
        secret=session_secret(),
    )


def validate_session_csrf(
    request: Request,
    supplied_token: str | None,
    expected_hash: str,
) -> bool:
    return validate_csrf(
        supplied_token=supplied_token or request.headers.get("X-CSRF-Token"),
        expected_hash=expected_hash,
        origin=request.headers.get("Origin"),
        allowed_origins=configured_origins(),
        secret=session_secret(),
    )
