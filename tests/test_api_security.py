"""Contrato de autenticação da API legada."""

from fastapi.testclient import TestClient
import pytest

import api
from webapp.security.config import validate_public_exposure


AUTH_HEADERS = {"X-API-Key": "pytest-api-key-not-for-production"}


@pytest.fixture
def client():
    # O context manager executa o ciclo de vida da aplicação e cria as tabelas
    # no banco temporário antes de cada teste.
    with TestClient(api.app) as test_client:
        yield test_client


def test_latest_rejects_anonymous_request(client):
    response = client.get("/readings/latest")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key inválida"}


def test_history_rejects_anonymous_request(client):
    response = client.get("/readings/history")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key inválida"}


def test_read_endpoints_accept_valid_api_key(client):
    latest = client.get("/readings/latest", headers=AUTH_HEADERS)
    history = client.get("/readings/history", headers=AUTH_HEADERS)

    assert latest.status_code == 200
    assert latest.json() == {}
    assert history.status_code == 200
    assert history.json() == []


def test_bulk_contract_still_requires_the_same_header(client):
    payload = {"readings": []}

    anonymous = client.post("/readings/bulk", json=payload)
    authenticated = client.post(
        "/readings/bulk",
        json=payload,
        headers=AUTH_HEADERS,
    )

    assert anonymous.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated.json() == {"status": "ok", "count": 0}


def test_public_exposure_hides_openapi(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_security_headers_are_applied(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["strict-transport-security"].startswith("max-age=")


def test_health_data_responses_are_never_cacheable(client):
    response = client.get("/readings/latest")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_public_exposure_rejects_weak_api_key():
    with pytest.raises(RuntimeError, match="pelo menos 32 caracteres"):
        validate_public_exposure("weak-key", public_exposure=True)


def test_local_mode_keeps_backward_compatibility_for_existing_keys():
    validate_public_exposure("legacy-local-key", public_exposure=False)
