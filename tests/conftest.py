"""Configuração global que isola os testes dos dados e segredos reais."""

import os
import sys
import tempfile
import gc
from pathlib import Path


_test_dir = tempfile.TemporaryDirectory(prefix="vitalis-pytest-", ignore_cleanup_errors=True)
_test_db = Path(_test_dir.name, "test.sqlite").resolve()

# Definir antes da coleta dos testes é essencial: models.py cria a engine no
# momento do import, e load_dotenv() não sobrescreve variáveis já existentes.
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.as_posix()}"
os.environ["API_KEY"] = "pytest-api-key-not-for-production"
os.environ["RING_ADDRESS"] = "00:00:00:00:00:00"
os.environ["API_URL"] = "http://127.0.0.1:8000"
os.environ["DEVICE_ID"] = "test-ring-01"
os.environ["ENV"] = "test"
os.environ["PUBLIC_EXPOSURE"] = "1"
os.environ["SESSION_SECRET"] = "pytest-session-secret-with-32-plus-characters"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["DEMO_MODE"] = "1"
os.environ["MAILER"] = "console"


def pytest_sessionfinish(session, exitstatus):
    """Fecha pools SQLite antes de remover o diretório temporário no Windows."""
    models = sys.modules.get("models")
    if models is not None:
        models.engine.dispose()
    gc.collect()
    _test_dir.cleanup()
