"""Configura o SMTP local sem expor credenciais no shell ou nos logs."""

from __future__ import annotations

import getpass
import os
import tempfile
from pathlib import Path

from webapp.security.magic_login import normalize_email, valid_email


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = "587"


class ConfigurationError(ValueError):
    """Indica uma configuração SMTP local inválida."""


def _single_line(value: str, field: str) -> str:
    value = value.strip()
    if not value or "\n" in value or "\r" in value:
        raise ConfigurationError(f"{field} deve ter um valor em uma única linha.")
    return value


def smtp_updates(
    *, host: str, port: str, user: str, password: str, sender: str
) -> dict[str, str]:
    host = _single_line(host, "Servidor SMTP")
    port = _single_line(port, "Porta SMTP")
    user = normalize_email(_single_line(user, "Usuário SMTP"))
    sender = normalize_email(_single_line(sender, "Remetente"))
    password = _single_line(password, "Senha de aplicativo")
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ConfigurationError("A porta SMTP deve estar entre 1 e 65535.")
    if not valid_email(user) or not valid_email(sender):
        raise ConfigurationError("Usuário SMTP e remetente devem ser e-mails válidos.")
    return {
        "MAILER": "smtp",
        "SMTP_HOST": host,
        "SMTP_PORT": port,
        "SMTP_USER": user,
        "SMTP_PASSWORD": password,
        "MAIL_FROM": sender,
    }


def update_env_text(original: str, updates: dict[str, str]) -> str:
    """Substitui chaves conhecidas uma vez e preserva o restante do arquivo."""
    pending = dict(updates)
    output: list[str] = []
    seen: set[str] = set()
    for line in original.splitlines():
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if key in updates and not stripped.startswith("#"):
            if key not in seen:
                output.append(f"{key}={updates[key]}")
                seen.add(key)
                pending.pop(key, None)
            continue
        output.append(line)
    if pending and output and output[-1] != "":
        output.append("")
    output.extend(f"{key}={value}" for key, value in pending.items())
    return "\n".join(output) + "\n"


def write_env_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    print("Configuração local de e-mail do Vitalis Ring")
    print("A credencial será salva somente no .env ignorado pelo Git.")
    provider = input("Provedor [gmail/outro] (gmail): ").strip().lower() or "gmail"
    if provider == "gmail":
        host, port = GMAIL_HOST, GMAIL_PORT
        print("Use a senha de aplicativo de 16 caracteres, não a senha comum do Gmail.")
    elif provider == "outro":
        host = input("Servidor SMTP: ").strip()
        port = input("Porta SMTP (587): ").strip() or GMAIL_PORT
    else:
        print("Provedor inválido. Use gmail ou outro.")
        return 1

    user = input("E-mail da conta remetente: ").strip()
    sender = input("E-mail exibido como remetente (Enter = mesma conta): ").strip() or user
    password = getpass.getpass("Senha de aplicativo SMTP: ")
    confirmation = getpass.getpass("Confirme a senha de aplicativo: ")
    if password != confirmation:
        print("As senhas não coincidem. Nada foi alterado.")
        return 1
    try:
        updates = smtp_updates(
            host=host, port=port, user=user, password=password, sender=sender
        )
    except ConfigurationError as exc:
        print(f"Configuração inválida: {exc}")
        return 1

    original = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    write_env_atomically(ENV_PATH, update_env_text(original, updates))
    print("SMTP_CONFIGURED:", True)
    print("Reinicie a API para carregar a configuração.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
