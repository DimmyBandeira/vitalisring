"""Integridade do esquema aditivo da área logada."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

import models
from webapp.models_app import Device, Patient


EXPECTED_TABLES = {
    "readings",
    "users",
    "login_tokens",
    "sessions",
    "patients",
    "devices",
    "care_links",
    "consents",
    "alerts",
    "access_log",
    "refresh_requests",
    "rate_limit_buckets",
}


def test_init_db_creates_only_additive_application_tables():
    models.init_db()

    assert EXPECTED_TABLES <= set(inspect(models.engine).get_table_names())
    reading_columns = {
        column["name"] for column in inspect(models.engine).get_columns("readings")
    }
    assert reading_columns == {
        "id",
        "device_id",
        "type",
        "value",
        "timestamp",
        "received_at",
    }


def test_device_public_id_is_unique_and_patient_is_single_device():
    models.init_db()
    db = models.SessionLocal()
    try:
        patient = Patient(display_name="Pessoa de teste", is_demo=True)
        db.add(patient)
        db.flush()
        db.add(Device(device_id="test-device-a", patient_id=patient.id, source="synthetic"))
        db.commit()

        db.add(Device(device_id="test-device-a", source="synthetic"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(Device(device_id="test-device-b", patient_id=patient.id, source="synthetic"))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_sqlite_foreign_keys_are_enforced():
    models.init_db()
    db = models.SessionLocal()
    try:
        db.add(Device(device_id="test-orphan", patient_id="missing-patient"))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
