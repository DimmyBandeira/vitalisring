"""Testes das ferramentas locais usadas no portão de hardware."""

import pytest

from models import SessionLocal, init_db
from tools.configure_smtp import ConfigurationError, smtp_updates, update_env_text
from tools.provision_demo_doctor import ProvisionError, create_demo_doctor
from tools.provision_technician import valid_password
from webapp.models_app import CareLink, Consent, Patient


def test_smtp_env_update_replaces_keys_without_duplicates():
    original = "ENV=dev\nMAILER=console\nSMTP_HOST=old.example\nMAILER=console\n"
    updates = smtp_updates(
        host="smtp.gmail.com",
        port="587",
        user="Sender@Example.com",
        password="app-password-test",
        sender="Sender@Example.com",
    )

    result = update_env_text(original, updates)

    assert result.count("MAILER=smtp") == 1
    assert "MAILER=console" not in result
    assert result.count("SMTP_HOST=smtp.gmail.com") == 1
    assert "SMTP_USER=sender@example.com" in result
    assert "SMTP_PASSWORD=app-password-test" in result
    assert result.startswith("ENV=dev\n")


@pytest.mark.parametrize(
    ("field", "value"),
    [("host", "smtp.example.com\nBAD=1"), ("port", "70000"), ("user", "not-an-email")],
)
def test_smtp_configuration_rejects_invalid_values(field, value):
    values = {
        "host": "smtp.example.com",
        "port": "587",
        "user": "sender@example.com",
        "password": "app-password-test",
        "sender": "sender@example.com",
    }
    values[field] = value
    with pytest.raises(ConfigurationError):
        smtp_updates(**values)


def test_technician_password_policy():
    assert valid_password("Senha-forte-123")
    assert not valid_password("curta1A")
    assert not valid_password("sem-maiuscula-123")
    assert not valid_password("SEM-MINUSCULA-123")
    assert not valid_password("SemNumeroAlgum")


def test_demo_doctor_is_linked_but_waits_for_family_consent():
    init_db()
    db = SessionLocal()
    patient = Patient(display_name="Paciente demonstrativo", is_demo=True)
    db.add(patient)
    db.commit()
    doctor = create_demo_doctor(
        db,
        full_name="Dra. Demonstração",
        email="demo-doctor-tool@example.test",
        password="Senha-forte-123",
        patient=patient,
    )
    assert doctor.role == "doctor"
    assert doctor.is_demo is True
    assert db.query(CareLink).filter(CareLink.user_id == doctor.id, CareLink.patient_id == patient.id).count() == 1
    assert db.query(Consent).filter(Consent.grantee_user_id == doctor.id).count() == 0
    db.close()


def test_demo_doctor_tool_refuses_real_patient():
    init_db()
    db = SessionLocal()
    patient = Patient(display_name="Paciente real", is_demo=False)
    db.add(patient)
    db.commit()
    with pytest.raises(ProvisionError, match="somente paciente de demonstração"):
        create_demo_doctor(
            db,
            full_name="Dra. Teste",
            email="real-doctor-tool@example.test",
            password="Senha-forte-123",
            patient=patient,
        )
    db.close()
