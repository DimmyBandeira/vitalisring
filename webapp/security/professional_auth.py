"""Senha Argon2, desafio MFA, TOTP cifrado e recuperação de uso único."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

import pyotp
import segno
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from markupsafe import Markup
from sqlalchemy.orm import Session

from models import utcnow_naive
from webapp.models_app import ProfessionalLoginChallenge, RecoveryCode, User
from webapp.security.crypto import new_token, token_hash
from webapp.security.sessions import session_secret


PROFESSIONAL_ROLES = {"doctor", "institution", "technician", "owner"}
CHALLENGE_TTL = timedelta(minutes=5)
MAX_MFA_ATTEMPTS = 5
_hasher = PasswordHasher()


@dataclass(frozen=True)
class MfaChallenge:
    token: str
    user: User


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("A senha deve ter pelo menos 12 caracteres")
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(session_secret().encode("utf-8")).digest())
    return Fernet(key)


def encrypt_totp_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_totp_secret(value: str) -> str | None:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError):
        return None


def issue_challenge(db: Session, user: User) -> MfaChallenge:
    raw = new_token()
    db.add(
        ProfessionalLoginChallenge(
            user_id=user.id,
            token_hash=token_hash(raw, session_secret()),
            expires_at=utcnow_naive() + CHALLENGE_TTL,
        )
    )
    db.commit()
    return MfaChallenge(raw, user)


def load_challenge(db: Session, raw: str | None) -> tuple[ProfessionalLoginChallenge, User] | None:
    if not raw:
        return None
    now = utcnow_naive()
    challenge = (
        db.query(ProfessionalLoginChallenge)
        .filter(
            ProfessionalLoginChallenge.token_hash == token_hash(raw, session_secret()),
            ProfessionalLoginChallenge.used_at.is_(None),
            ProfessionalLoginChallenge.expires_at > now,
            ProfessionalLoginChallenge.attempts < MAX_MFA_ATTEMPTS,
        )
        .first()
    )
    if challenge is None:
        return None
    user = db.get(User, challenge.user_id)
    if user is None or not user.is_active or user.role not in PROFESSIONAL_ROLES:
        return None
    return challenge, user


def ensure_totp(user: User, db: Session) -> str:
    secret = decrypt_totp_secret(user.totp_secret_encrypted) if user.totp_secret_encrypted else None
    if secret:
        return secret
    secret = pyotp.random_base32()
    user.totp_secret_encrypted = encrypt_totp_secret(secret)
    db.commit()
    return secret


def totp_qr_svg(user: User, secret: str) -> Markup:
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Vitalis Ring")
    return Markup(segno.make(uri).svg_inline(scale=4, omitsize=True))


def mfa_is_configured(db: Session, user: User) -> bool:
    return db.query(RecoveryCode).filter(RecoveryCode.user_id == user.id).count() > 0


def create_recovery_codes(db: Session, user: User) -> list[str]:
    db.query(RecoveryCode).filter(RecoveryCode.user_id == user.id).delete()
    raw_codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(8)]
    for raw in raw_codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=token_hash(raw, session_secret())))
    db.commit()
    return raw_codes


def verify_second_factor(db: Session, user: User, code: str) -> bool:
    normalized = code.strip().replace(" ", "")
    secret = decrypt_totp_secret(user.totp_secret_encrypted or "")
    if secret and pyotp.TOTP(secret).verify(normalized, valid_window=1):
        return True
    wanted = token_hash(normalized.casefold(), session_secret())
    recovery = (
        db.query(RecoveryCode)
        .filter(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == wanted,
            RecoveryCode.used_at.is_(None),
        )
        .first()
    )
    if recovery:
        recovery.used_at = utcnow_naive()
        db.commit()
        return True
    return False


def verify_totp_code(user: User, code: str) -> bool:
    secret = decrypt_totp_secret(user.totp_secret_encrypted or "")
    return bool(secret and pyotp.TOTP(secret).verify(code.strip(), valid_window=1))


def fail_challenge(db: Session, challenge: ProfessionalLoginChallenge) -> None:
    challenge.attempts += 1
    db.commit()


def consume_challenge(db: Session, challenge: ProfessionalLoginChallenge) -> None:
    challenge.used_at = utcnow_naive()
    db.commit()
