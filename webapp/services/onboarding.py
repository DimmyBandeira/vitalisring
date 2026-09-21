"""Cadastro atômico de cliente, paciente e dispositivo pelo técnico."""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Reading, utcnow_naive
from webapp.models_app import CareLink, Device, Patient, User
from webapp.security.magic_login import normalize_email, valid_email


class OnboardingError(ValueError):
    pass


@dataclass(frozen=True)
class OnboardingResult:
    customer: User
    patient: Patient
    device: Device


def create_customer_onboarding(
    db: Session,
    *,
    technician: User,
    customer_name: str,
    customer_email: str,
    patient_name: str,
    device_id: str,
    serial_number: str | None,
    source: str,
) -> OnboardingResult:
    normalized_email = normalize_email(customer_email)
    normalized_device = device_id.strip()
    normalized_serial = (serial_number or "").strip() or None
    customer_name = customer_name.strip()
    patient_name = patient_name.strip()
    if technician.role not in {"technician", "owner"}:
        raise OnboardingError("Usuário sem permissão técnica")
    if not customer_name or not patient_name or not valid_email(normalized_email):
        raise OnboardingError("Preencha os dados obrigatórios corretamente")
    if source not in {"synthetic", "physical"}:
        raise OnboardingError("Origem do dispositivo inválida")
    if not normalized_device:
        raise OnboardingError("Identificador do dispositivo é obrigatório")
    if source == "synthetic" and not normalized_device.startswith("demo-"):
        raise OnboardingError("Dispositivo sintético deve usar identificador demo-*")
    if db.query(User).filter(User.email == normalized_email).first():
        raise OnboardingError("E-mail já cadastrado")
    if db.query(Device).filter(Device.device_id == normalized_device).first():
        raise OnboardingError("Dispositivo já cadastrado")
    if normalized_serial and db.query(Device).filter(Device.serial_number == normalized_serial).first():
        raise OnboardingError("Número de série já cadastrado")

    is_demo = source == "synthetic"
    customer = User(
        email=normalized_email,
        full_name=customer_name,
        role="customer",
        is_demo=is_demo,
    )
    patient = Patient(display_name=patient_name, is_demo=is_demo)
    try:
        db.add_all([customer, patient])
        db.flush()
        device = Device(
            device_id=normalized_device,
            serial_number=normalized_serial,
            patient_id=patient.id,
            source=source,
            status="pending",
            registered_by=technician.id,
        )
        db.add(device)
        db.add(
            CareLink(
                user_id=customer.id,
                patient_id=patient.id,
                link_type="guardian",
                created_by=technician.id,
            )
        )
        db.commit()
        db.refresh(customer)
        db.refresh(patient)
        db.refresh(device)
    except IntegrityError as exc:
        db.rollback()
        raise OnboardingError("Cadastro duplicado ou inconsistente") from exc
    return OnboardingResult(customer=customer, patient=patient, device=device)


def activate_synthetic_device(db: Session, *, device: Device, technician: User) -> None:
    if technician.role not in {"technician", "owner"}:
        raise OnboardingError("Usuário sem permissão técnica")
    if technician.role == "technician" and device.registered_by != technician.id:
        raise OnboardingError("Dispositivo fora do escopo deste técnico")
    if device.source != "synthetic":
        raise OnboardingError("Ativação sintética não permitida para dispositivo físico")
    refresh_synthetic_device(db, device=device)


def refresh_synthetic_device(db: Session, *, device: Device) -> None:
    if device.source != "synthetic":
        raise OnboardingError("Leitura sintética não permitida para dispositivo físico")
    now = utcnow_naive()
    db.add_all(
        [
            Reading(device_id=device.device_id, type="heart_rate", value=72, timestamp=now),
            Reading(device_id=device.device_id, type="spo2", value=97, timestamp=now),
            Reading(device_id=device.device_id, type="battery", value=84, timestamp=now),
        ]
    )
    device.status = "active"
    device.activated_at = now
    db.commit()


def unassign_device(db: Session, *, device: Device, technician: User) -> str | None:
    if technician.role not in {"technician", "owner"}:
        raise OnboardingError("Usuário sem permissão técnica")
    if technician.role == "technician" and device.registered_by != technician.id:
        raise OnboardingError("Dispositivo fora do escopo deste técnico")
    previous_patient_id = device.patient_id
    device.patient_id = None
    device.status = "unassigned"
    device.activated_at = None
    db.commit()
    return previous_patient_id
