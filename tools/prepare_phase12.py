"""Completa apenas a configuração local ausente para a Fase 12."""

import secrets
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
LOCAL_BASE_URL = "http://localhost:8000"


def main() -> None:
    original = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    keys = {
        line.split("=", 1)[0].strip()
        for line in original.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
    }
    additions = []
    if "SESSION_SECRET" not in keys:
        additions.append(f"SESSION_SECRET={secrets.token_urlsafe(48)}")
    if "PUBLIC_BASE_URL" not in keys:
        additions.append(f"PUBLIC_BASE_URL={LOCAL_BASE_URL}")
    if "ENV" not in keys:
        additions.append("ENV=dev")
    if "DEMO_MODE" not in keys:
        additions.append("DEMO_MODE=1")
    if "MAILER" not in keys:
        additions.append("MAILER=console")
    lines = original.splitlines()
    lines = [
        f"PUBLIC_BASE_URL={LOCAL_BASE_URL}" if line.startswith("PUBLIC_BASE_URL=") else line
        for line in lines
    ]
    normalized = "\n".join(lines)
    if original.endswith("\n"):
        normalized += "\n"
    if additions:
        separator = "" if not normalized or normalized.endswith("\n") else "\n"
        normalized += separator + "\n".join(additions) + "\n"
    if normalized != original:
        ENV_PATH.write_text(normalized, encoding="utf-8")
    print("PHASE12_LOCAL_CONFIG_READY:", True)
    print("ADDED_KEYS:", len(additions))


if __name__ == "__main__":
    main()
