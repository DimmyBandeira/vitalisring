"""Proteção CSRF por token de sessão e comparação exata de origem."""

from urllib.parse import urlsplit

from webapp.security.crypto import constant_time_equal, token_hash


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
