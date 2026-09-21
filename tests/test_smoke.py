"""Testes mínimos do projeto legado antes da expansão da aplicação web."""

import py_compile
from pathlib import Path

from sqlalchemy import inspect


ROOT = Path(__file__).resolve().parents[1]


def test_python_modules_compile():
    for relative_path in (
        "api.py",
        "models.py",
        "collector.py",
        "dashboard.py",
        "scan_raw.py",
        "test_spo2.py",
    ):
        py_compile.compile(ROOT / relative_path, doraise=True)


def test_core_modules_import_with_isolated_database():
    import api
    import collector
    import models

    database_path = Path(models.engine.url.database).resolve()

    assert "vitalis-pytest-" in str(database_path.parent)
    assert database_path.name == "test.sqlite"
    assert api.API_KEY == "pytest-api-key-not-for-production"
    assert collector.DEVICE_ID == "test-ring-01"

    models.init_db()
    assert "readings" in inspect(models.engine).get_table_names()
