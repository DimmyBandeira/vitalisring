"""Testes das ferramentas locais usadas no portão de hardware."""

import pytest

from models import SessionLocal, init_db
from tools.provision_demo_doctor import ProvisionError, create_demo_doctor
from tools.provision_technician import valid_password
from webapp.models_app import CareLink, Consent, Patient


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
