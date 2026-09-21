"""Contrato de autenticação da API legada."""

from fastapi.testclient import TestClient
import pytest

import api


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
