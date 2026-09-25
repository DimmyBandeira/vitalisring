"""Provisiona o primeiro técnico real sem expor a senha no shell ou em logs."""

import getpass
import re

from sqlalchemy.exc import IntegrityError

from models import SessionLocal, init_db
from webapp.models_app import User
from webapp.security.magic_login import normalize_email, valid_email
from webapp.security.professional_auth import hash_password


def valid_password(password: str) -> bool:
    return (
        len(password) >= 12
        and bool(re.search(r"[A-Z]", password))
        and bool(re.search(r"[a-z]", password))
        and bool(re.search(r"[0-9]", password))
    )


def main() -> int:
    init_db()
    print("Provisionamento local do técnico Vitalis")
    full_name = input("Nome completo: ").strip()
    email = normalize_email(input("E-mail: "))
    password = getpass.getpass("Senha (12+ caracteres, maiúscula, minúscula e número): ")
    confirmation = getpass.getpass("Confirme a senha: ")
    if not full_name or not valid_email(email):
        print("Nome ou e-mail inválido.")
        return 1
    if password != confirmation:
        print("As senhas não coincidem.")
        return 1
    if not valid_password(password):
        print("A senha não atende aos requisitos.")
        return 1

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print("Já existe uma conta com esse e-mail.")
            return 1
        db.add(
            User(
                email=email,
                full_name=full_name,
                role="technician",
                password_hash=hash_password(password),
                is_demo=False,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        print("Não foi possível criar a conta; verifique se ela já existe.")
        return 1
    finally:
        db.close()
    print("Técnico criado. Feche esta janela e volte ao navegador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
