"""Entrega de autenticação por console seguro ou SMTP."""

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


logger = logging.getLogger("vitalis.mailer")


@dataclass(frozen=True)
class LoginDelivery:
    recipient: str
    magic_link: str
    code: str


class Mailer(Protocol):
    def send_login(self, delivery: LoginDelivery) -> None: ...


class ConsoleMailer:
    def send_login(self, delivery: LoginDelivery) -> None:
        # Não registrar destinatário, token, código nem link. A prévia de demo é
        # devolvida diretamente à rota somente para usuários sintéticos.
        logger.info("Solicitação de login preparada pelo canal console")


class SMTPMailer:
    def __init__(self) -> None:
        self.host = os.environ["SMTP_HOST"]
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.sender = os.environ["MAIL_FROM"]

    def send_login(self, delivery: LoginDelivery) -> None:
        message = EmailMessage()
        message["Subject"] = "Seu acesso ao Vitalis Ring"
        message["From"] = self.sender
        message["To"] = delivery.recipient
        message.set_content(
            "Use o link abaixo para entrar no Vitalis Ring. Ele expira em 15 minutos.\n\n"
            f"{delivery.magic_link}\n\n"
            f"Se preferir, use o código: {delivery.code}\n\n"
            "Se você não solicitou este acesso, ignore esta mensagem."
        )
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)


def configured_mailer() -> Mailer:
    channel = os.environ.get("MAILER", "console").strip().lower()
    if channel == "smtp":
        return SMTPMailer()
    return ConsoleMailer()
