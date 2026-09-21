"""Núcleo do login sem senha, sem depender das telas."""

from urllib.parse import parse_qs, urlsplit

import pytest

from models import SessionLocal, init_db, utcnow_naive
from webapp.models_app import LoginToken, User
from webapp.security.config import validate_demo_mode
from webapp.security.magic_login import (
    REQUEST_LIMIT,
    consume_login_code,
    consume_magic_token,
    request_login,
)
from webapp.services.mailer import ConsoleMailer, LoginDelivery


class CaptureMailer:
    def __init__(self):
        self.deliveries: list[LoginDelivery] = []

    def send_login(self, delivery: LoginDelivery) -> None:
        self.deliveries.append(delivery)


def create_customer(*, is_demo: bool = True) -> User:
    init_db()
    db = SessionLocal()
    suffix = str(utcnow_naive().timestamp()).replace(".", "")
    user = User(
        email=f"cliente-{suffix}@example.test",
        full_name="Cliente de demonstração",
        role="customer",
        is_demo=is_demo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.expunge(user)
    db.close()
    return user


def request_for(user: User, mailer: CaptureMailer, *, ip: str = "192.0.2.10"):
    db = SessionLocal()
    preview = request_login(
        db,
        email=user.email,
        ip=ip,
        public_base_url="https://demo.vitalis.test",
        mailer=mailer,
        demo_mode=True,
    )
    db.close()
    return preview


def test_magic_token_and_code_are_single_use_and_only_hashes_are_stored():
    user = create_customer()
    mailer = CaptureMailer()
    preview = request_for(user, mailer)

    assert preview is not None
    assert len(mailer.deliveries) == 1
    raw_token = parse_qs(urlsplit(preview.magic_link).query)["token"][0]
    db = SessionLocal()
    record = db.query(LoginToken).filter(LoginToken.user_id == user.id).one()
    assert raw_token not in record.token_hash
    assert preview.code not in record.code_hash
    assert consume_magic_token(db, raw_token).id == user.id
    assert consume_magic_token(db, raw_token) is None
    db.close()

    second = request_for(user, mailer, ip="192.0.2.11")
    db = SessionLocal()
    assert consume_login_code(db, user.email, second.code).id == user.id
    assert consume_login_code(db, user.email, second.code) is None
    db.close()


def test_unknown_email_has_neutral_result_and_no_delivery():
    init_db()
    db = SessionLocal()
    mailer = CaptureMailer()

    result = request_login(
        db,
        email="nao-existe@example.test",
        ip="192.0.2.20",
        public_base_url="https://demo.vitalis.test",
        mailer=mailer,
        demo_mode=True,
    )

    assert result is None
    assert mailer.deliveries == []
    db.close()


def test_rate_limit_is_neutral_after_the_limit():
    user = create_customer()
    mailer = CaptureMailer()
    results = [request_for(user, mailer, ip="192.0.2.30") for _ in range(REQUEST_LIMIT + 1)]

    assert all(result is not None for result in results[:REQUEST_LIMIT])
    assert results[-1] is None
    assert len(mailer.deliveries) == REQUEST_LIMIT


def test_console_mailer_does_not_log_recipient_or_credentials(caplog):
    delivery = LoginDelivery(
        recipient="pessoa@example.test",
        magic_link="https://demo.vitalis.test/login/token?token=segredo",
        code="123456",
    )

    ConsoleMailer().send_login(delivery)

    output = caplog.text
    assert "pessoa@example.test" not in output
    assert "segredo" not in output
    assert "123456" not in output


def test_production_refuses_demo_mode():
    with pytest.raises(RuntimeError, match="não permite DEMO_MODE"):
        validate_demo_mode("prod", True)
    validate_demo_mode("prod", False)
