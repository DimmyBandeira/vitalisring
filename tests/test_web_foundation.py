"""Integração entre o site estático e as páginas FastAPI da mesma origem."""

import re

import pytest
from fastapi.testclient import TestClient

import api


PLACEHOLDER_ROUTES = (
    "/perguntas-frequentes/",
    "/seguranca-e-privacidade/",
    "/agendar-demonstracao/",
    "/programa-piloto-medicos/",
    "/contato/",
    "/termos-de-uso/",
    "/politica-de-privacidade/",
    "/politica-de-cookies/",
)

FAMILY_ROUTES = ("/familias/", "/para-familias/")
MEDICAL_ROUTES = ("/medicos/", "/para-medicos/")
INSTITUTION_ROUTES = ("/instituicoes/", "/para-instituicoes/")


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
    app_response = client.get("/app", follow_redirects=False)
    logout_response = client.get("/logout", follow_redirects=False)

    assert app_response.status_code == 303
    assert app_response.headers["location"] == "/login"
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"
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


@pytest.mark.parametrize("route", FAMILY_ROUTES)
def test_family_landing_page_is_complete(client, route):
    response = client.get(route)

    assert response.status_code == 200
    assert response.text.lower().count("<h1") == 1
    assert "A tranquilidade de saber que quem você ama está bem" in response.text
    assert "O que você recebe no WhatsApp" in response.text
    assert response.text.count("<details") == 4
    assert '/familias/imagens/rotina-com-anel.jpg' in response.text
    assert '/familias/imagens/familiar-no-celular.jpg' in response.text
    assert 'href="https://vitalisring.com.br/familias/"' in response.text


def test_family_primary_route_is_indexable_and_legacy_route_is_noindex(client):
    primary = client.get("/familias/")
    legacy = client.get("/para-familias/")

    assert 'content="index,follow,max-image-preview:large"' in primary.text
    assert 'content="noindex,follow"' in legacy.text


@pytest.mark.parametrize("route", MEDICAL_ROUTES)
def test_medical_landing_page_is_complete(client, route):
    response = client.get(route)

    assert response.status_code == 200
    assert response.text.lower().count("<h1") == 1
    assert "Do dado pontual no consultório ao" in response.text
    assert "filme contínuo" in response.text
    assert "A Lacuna do Cuidado Episódico" in response.text
    assert "Console Clínico &amp; Tendências" in response.text
    assert "Dados fictícios — demonstração" in response.text
    assert response.text.count("<details") == 3
    assert '/medicos/imagens/especialista-console.webp' in response.text
    assert '/medicos/imagens/anel-sensor-ppg.webp' in response.text
    assert "Representação conceitual, sem certificação técnica" in response.text
    assert 'href="https://vitalisring.com.br/medicos/"' in response.text


def test_medical_primary_route_is_indexable_and_legacy_route_is_noindex(client):
    primary = client.get("/medicos/")
    legacy = client.get("/para-medicos/")

    assert 'content="index,follow,max-image-preview:large"' in primary.text
    assert 'content="noindex,follow"' in legacy.text


@pytest.mark.parametrize("route", INSTITUTION_ROUTES)
def test_institution_landing_page_is_complete(client, route):
    response = client.get(route)

    assert response.status_code == 200
    assert response.text.lower().count("<h1") == 1
    assert "Segurança contínua para seus residentes." in response.text
    assert "Três gargalos que pesam sobre a equipe" in response.text
    assert "Dashboard de Gestão de Pavilhões" in response.text
    assert "Quarto 204 · Sr. Roberto" in response.text
    assert "Dados fictícios — demonstração" in response.text
    assert response.text.count("<details") == 3
    assert "/instituicoes/imagens/residente-rotina.webp" in response.text
    assert "/instituicoes/imagens/equipe-posto-enfermagem.webp" in response.text
    assert "Não substitui equipamentos médicos de suporte à vida" in response.text
    assert 'href="https://vitalisring.com.br/instituicoes/"' in response.text


def test_institution_primary_route_is_indexable_and_legacy_route_is_noindex(client):
    primary = client.get("/instituicoes/")
    legacy = client.get("/para-instituicoes/")

    assert 'content="index,follow,max-image-preview:large"' in primary.text
    assert 'content="noindex,follow"' in legacy.text
    assert client.get("/instituicoes/imagens/residente-rotina.webp").status_code == 200

def test_how_it_works_page_is_complete_and_indexable(client):
    response = client.get("/como-funciona/")

    assert response.status_code == 200
    assert response.text.lower().count("<h1") == 1
    assert "Do seu dedo ao WhatsApp da família." in response.text
    assert "O motor de análise SAFE" in response.text
    assert "Anatomia do hardware" in response.text
    assert "Dados fictícios — demonstração" in response.text
    assert response.text.count("<details") == 4
    assert "/como-funciona/imagens/anel-e-aplicativo.webp" in response.text
    assert "/como-funciona/imagens/anatomia-conceitual.webp" in response.text
    assert "não substitui serviços de emergência (como o 192)" in response.text
    assert 'content="index,follow,max-image-preview:large"' in response.text
    assert client.get("/como-funciona/imagens/anatomia-conceitual.webp").status_code == 200

def test_waitlist_page_has_compliant_form(client):
    response = client.get("/lista-de-espera/")
    html = response.text

    assert response.status_code == 200
    assert html.lower().count("<h1") == 1
    assert "Garanta seu lugar no" in html
    assert 'action="/api/lista-de-espera" method="post"' in html
    for field in ('name="nome"', 'name="whatsapp"', 'name="email"', 'name="website"'):
        assert field in html
    assert html.count('name="objetivo"') == 4
    assert 'name="consentimento" value="on" required' in html
    assert 'href="/politica-de-privacidade/"' in html
    assert "Você está na lista de espera!" in html
    assert "site-header-minimal" in html
    assert 'content="index,follow,max-image-preview:large"' in html
    assert client.get("/lista-de-espera/imagens/anel-e-kit-de-aros.webp").status_code == 200


def test_waitlist_copy_has_no_fabricated_scarcity_or_absolute_claims(client):
    text = client.get("/lista-de-espera/").text

    assert "%" not in re.sub(r"<style.*?</style>|style=\"[^\"]*\"", "", text, flags=re.S)
    assert "100" not in re.sub(r"<[^>]+>", " ", text)
    assert "Vagas Limitadas" not in text


def test_thank_you_page_is_noindex(client):
    response = client.get("/obrigado/")

    assert response.status_code == 200
    assert "Você está na lista de espera!" in response.text
    assert 'content="noindex,follow"' in response.text

def test_unknown_public_route_uses_the_custom_404(client):
    response = client.get("/pagina-que-nao-existe/")

    assert response.status_code == 404
    assert "Página não encontrada" in response.text
