"""Cria um médico para a demonstração sem conceder consentimento em nome da família."""

import getpass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import SessionLocal, init_db
from tools.provision_technician import valid_password
from webapp.models_app import CareLink, Device, Patient, User
from webapp.security.magic_login import normalize_email, valid_email
from webapp.security.professional_auth import hash_password


class ProvisionError(ValueError):
    pass


def create_demo_doctor(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    patient: Patient,
) -> User:
    normalized_email = normalize_email(email)
    if not full_name.strip() or not valid_email(normalized_email):
        raise ProvisionError("Nome ou e-mail inválido.")
    if not valid_password(password):
        raise ProvisionError("A senha não atende aos requisitos.")
    if not patient.is_demo:
        raise ProvisionError("Esta ferramenta aceita somente paciente de demonstração.")
    if db.query(User).filter(User.email == normalized_email).first():
        raise ProvisionError("Já existe uma conta com esse e-mail.")

    doctor = User(
        email=normalized_email,
        full_name=full_name.strip(),
        role="doctor",
        password_hash=hash_password(password),
        is_demo=True,
    )
    db.add(doctor)
    db.flush()
    db.add(CareLink(user_id=doctor.id, patient_id=patient.id, link_type="doctor"))
    db.commit()
    db.refresh(doctor)
    return doctor


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        devices = (
            db.query(Device)
            .join(Patient, Patient.id == Device.patient_id)
            .filter(Device.source == "synthetic", Patient.is_demo.is_(True))
            .order_by(Device.created_at.desc())
            .all()
        )
        if not devices:
            print("Nenhum paciente sintético disponível.")
            return 1
        device = devices[0]
        patient = db.get(Patient, device.patient_id)
        print("Provisionamento local do médico de demonstração")
        print(f"Cenário selecionado: {device.device_id}")
        full_name = input("Nome completo do médico: ").strip()
        email = input("E-mail profissional: ")
        password = getpass.getpass("Senha (12+ caracteres, maiúscula, minúscula e número): ")
        confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            print("As senhas não coincidem.")
            return 1
        create_demo_doctor(
            db,
            full_name=full_name,
            email=email,
            password=password,
            patient=patient,
        )
    except ProvisionError as exc:
        db.rollback()
        print(str(exc))
        return 1
    except IntegrityError:
        db.rollback()
        print("Não foi possível criar a conta médica.")
        return 1
    finally:
        db.close()
    print("Médico criado e vinculado. O consentimento continua aguardando a família.")
    print("Pressione Enter para fechar e volte ao navegador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
