"""Validação central das opções que afetam exposição pública."""

import os


TRUE_VALUES = {"1", "true", "yes", "on"}
KNOWN_UNSAFE_KEYS = {
    "changeme",
    "change-me",
    "sua-chave-aqui",
    "your-api-key",
}


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def validate_public_exposure(
    api_key: str,
    public_exposure: bool,
    session_secret: str | None = None,
) -> None:
    """Recusa iniciar uma aplicação publicamente exposta com chave insegura."""
    if not api_key:
        raise RuntimeError("API_KEY não configurada")
    if not public_exposure:
        return

    normalized = api_key.strip().lower()
    if len(api_key) < 32 or normalized in KNOWN_UNSAFE_KEYS:
        raise RuntimeError(
            "PUBLIC_EXPOSURE=1 exige API_KEY aleatória com pelo menos 32 caracteres"
        )
    if session_secret is not None and len(session_secret) < 32:
        raise RuntimeError(
            "PUBLIC_EXPOSURE=1 exige SESSION_SECRET com pelo menos 32 caracteres"
        )


def validate_demo_mode(environment: str, demo_mode: bool) -> None:
    if environment.strip().lower() == "prod" and demo_mode:
        raise RuntimeError("ENV=prod não permite DEMO_MODE=1")
