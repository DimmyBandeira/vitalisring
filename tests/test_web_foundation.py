"""Integração entre o site estático e as páginas FastAPI da mesma origem."""

import re

import pytest
from fastapi.testclient import TestClient

import api


PLACEHOLDER_ROUTES = (
    "/para-familias/",
    "/para-medicos/",
    "/para-instituicoes/",
    "/como-funciona/",
    "/perguntas-frequentes/",
    "/seguranca-e-privacidade/",
    "/lista-de-espera/",
    "/agendar-demonstracao/",
    "/programa-piloto-medicos/",
    "/contato/",
    "/termos-de-uso/",
    "/politica-de-privacidade/",
    "/politica-de-cookies/",
)


@pytest.fixture
def client():
    with TestClient(api.app) as test_client:
        yield test_client


def test_public_site_and_login_share_the_same_origin(client):
    home = client.get("/")
    login = client.get("/login")

    assert home.status_code == 200
    assert 'href="/login"' in home.text
    assert login.status_code == 200
    assert "Entre no Vitalis" in login.text


def test_app_routes_are_not_captured_by_public_site_mount(client):
    assert client.get("/app").status_code == 200
    assert client.get("/logout").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_app_uses_only_local_browser_assets(client):
    response = client.get("/login")
    browser_urls = re.findall(r'(?:src|href)="([^"]+)"', response.text)

    assert client.get("/static/app.css").status_code == 200
    assert client.get("/static/vendor/htmx.min.js").status_code == 200
    assert client.get("/design/tokens.css").status_code == 200
    assert browser_urls
    assert not [url for url in browser_urls if url.startswith(("http://", "https://", "//"))]


@pytest.mark.parametrize("route", PLACEHOLDER_ROUTES)
def test_placeholder_routes_exist_and_are_noindex(client, route):
    response = client.get(route)

    assert response.status_code == 200
    assert response.text.lower().count("<h1") == 1
    assert '<meta name="robots" content="noindex,follow">' in response.text
    assert "Voltar ao início" in response.text


def test_unknown_public_route_uses_the_custom_404(client):
    response = client.get("/pagina-que-nao-existe/")

    assert response.status_code == 404
    assert "Página não encontrada" in response.text
