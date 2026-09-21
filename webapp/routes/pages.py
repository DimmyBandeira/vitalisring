"""Páginas iniciais da área logada, ainda sem autenticação funcional."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"page_title": "Entrar | Vitalis Ring"},
    )


@router.get("/app", response_class=HTMLResponse)
def app_home_placeholder(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="app_home.html",
        context={"page_title": "Área Vitalis | Vitalis Ring"},
    )


@router.get("/logout", response_class=HTMLResponse)
def logout_placeholder(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="logout.html",
        context={"page_title": "Sessão encerrada | Vitalis Ring"},
    )
