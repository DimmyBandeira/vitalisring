"""Sessões opacas revogáveis, com expiração deslizante e limite absoluto."""

import os
from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from models import SessionLocal, utcnow_naive
from webapp.models_app import AppSession, User
from webapp.security.crypto import new_token, token_hash


COOKIE_NAME = "vr_session"
CSRF_COOKIE_NAME = "vr_csrf"
SESSION_TTL = timedelta(days=30)
SESSION_ABSOLUTE_TTL = timedelta(days=45)


@dataclass(frozen=True)
class NewSession:
    token: str
    csrf_token: str
    record: AppSession


def session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET deve ter pelo menos 32 caracteres")
    return secret


def create_session(db: Session, user: User) -> NewSession:
    now = utcnow_naive()
    raw_token = new_token()
    raw_csrf = new_token()
    secret = session_secret()
    record = AppSession(
        user_id=user.id,
        token_hash=token_hash(raw_token, secret),
        csrf_hash=token_hash(raw_csrf, secret),
        created_at=now,
        last_seen_at=now,
        expires_at=now + SESSION_TTL,
        absolute_expires_at=now + SESSION_ABSOLUTE_TTL,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return NewSession(token=raw_token, csrf_token=raw_csrf, record=record)


def resolve_session(db: Session, raw_token: str | None) -> tuple[AppSession, User] | None:
    if not raw_token:
        return None
    secret = session_secret()
    record = (
        db.query(AppSession)
        .filter(AppSession.token_hash == token_hash(raw_token, secret))
        .first()
    )
    now = utcnow_naive()
    if (
        record is None
        or record.revoked_at is not None
        or record.expires_at <= now
        or record.absolute_expires_at <= now
    ):
        return None
    user = db.query(User).filter(User.id == record.user_id, User.is_active.is_(True)).first()
    if user is None:
        return None

    record.last_seen_at = now
    record.expires_at = min(now + SESSION_TTL, record.absolute_expires_at)
    db.commit()
    return record, user


def revoke_session(db: Session, record: AppSession) -> None:
    record.revoked_at = utcnow_naive()
    db.commit()


def secure_cookie_enabled() -> bool:
    environment = os.environ.get("ENV", "dev").strip().lower()
    base_url = os.environ.get("PUBLIC_BASE_URL", "")
    return environment not in {"dev", "test"} or base_url.startswith("https://")


def set_session_cookies(response: Response, new_session: NewSession) -> None:
    secure = secure_cookie_enabled()
    max_age = int(SESSION_TTL.total_seconds())
    response.set_cookie(
        COOKIE_NAME,
        new_session.token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        new_session.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", samesite="lax")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", samesite="lax")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def authenticated_context(request: Request, db: Session) -> tuple[AppSession, User]:
    resolved = resolve_session(db, request.cookies.get(COOKIE_NAME))
    if resolved is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    return resolved
