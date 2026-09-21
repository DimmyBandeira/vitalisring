"""Funções pequenas para tokens opacos e hashes autenticados."""

import hashlib
import hmac
import secrets


def new_token(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)


def token_hash(value: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
