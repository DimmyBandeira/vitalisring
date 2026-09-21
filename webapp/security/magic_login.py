"""Emissão e consumo de links mágicos e códigos de seis dígitos."""

import re
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from models import utcnow_naive
from webapp.models_app import LoginToken, User
from webapp.security.crypto import new_token, token_hash
from webapp.security.ratelimit import consume
from webapp.security.sessions import session_secret
from webapp.services.mailer import LoginDelivery, Mailer


TOKEN_TTL = timedelta(minutes=15)
REQUEST_WINDOW = timedelta(minutes=15)
REQUEST_LIMIT = 5
CODE_ATTEMPT_LIMIT = 5
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class DemoPreview:
    magic_link: str
    code: str


def normalize_email(value: str) -> str:
    return value.strip().casefold()[:320]


def valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(value))


def request_login(
    db: Session,
    *,
    email: str,
    ip: str,
    public_base_url: str,
    mailer: Mailer,
    demo_mode: bool,
) -> DemoPreview | None:
    normalized = normalize_email(email)
    secret = session_secret()
    allowed_ip = consume(
        db,
        scope="login-ip",
        identifier=ip,
        secret=secret,
        limit=REQUEST_LIMIT,
        window=REQUEST_WINDOW,
    )
    allowed_email = consume(
        db,
        scope="login-email",
        identifier=normalized,
        secret=secret,
        limit=REQUEST_LIMIT,
        window=REQUEST_WINDOW,
    )
    if not valid_email(normalized) or not (allowed_ip and allowed_email):
        return None
    user = db.query(User).filter(User.email == normalized, User.is_active.is_(True)).first()
    if user is None or user.role != "customer":
        return None

    raw_token = new_token()
    raw_code = f"{secrets.randbelow(1_000_000):06d}"
    login_token = LoginToken(
        user_id=user.id,
        token_hash=token_hash(raw_token, secret),
        code_hash=token_hash(raw_code, secret),
        expires_at=utcnow_naive() + TOKEN_TTL,
    )
    db.add(login_token)
    db.commit()
    link = f"{public_base_url.rstrip('/')}/login/token?token={raw_token}"
    mailer.send_login(LoginDelivery(normalized, link, raw_code))
    if demo_mode and user.is_demo:
        return DemoPreview(magic_link=link, code=raw_code)
    return None


def consume_magic_token(db: Session, raw_token: str) -> User | None:
    now = utcnow_naive()
    record = (
        db.query(LoginToken)
        .filter(
            LoginToken.token_hash == token_hash(raw_token, session_secret()),
            LoginToken.used_at.is_(None),
            LoginToken.expires_at > now,
        )
        .first()
    )
    if record is None:
        return None
    user = db.query(User).filter(User.id == record.user_id, User.is_active.is_(True)).first()
    if user is None:
        return None
    record.used_at = now
    db.commit()
    return user


def consume_login_code(db: Session, email: str, raw_code: str) -> User | None:
    normalized = normalize_email(email)
    if not valid_email(normalized) or not re.fullmatch(r"\d{6}", raw_code):
        return None
    user = db.query(User).filter(User.email == normalized, User.is_active.is_(True)).first()
    if user is None or user.role != "customer":
        return None
    now = utcnow_naive()
    records = (
        db.query(LoginToken)
        .filter(
            LoginToken.user_id == user.id,
            LoginToken.used_at.is_(None),
            LoginToken.expires_at > now,
            LoginToken.attempts < CODE_ATTEMPT_LIMIT,
        )
        .order_by(LoginToken.created_at.desc())
        .all()
    )
    wanted_hash = token_hash(raw_code, session_secret())
    for record in records:
        record.attempts += 1
        if secrets.compare_digest(record.code_hash, wanted_hash):
            record.used_at = now
            db.commit()
            return user
    db.commit()
    return None
