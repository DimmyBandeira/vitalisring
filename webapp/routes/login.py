"""Login B2C por link mágico ou código de seis dígitos."""

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from webapp.routes.common import templates
from webapp.security.config import env_flag
from webapp.security.csrf import LOGIN_CSRF_COOKIE, issue_login_csrf, validate_login_csrf
from webapp.security.magic_login import consume_login_code, consume_magic_token, request_login
from webapp.security.sessions import create_session, get_db, secure_cookie_enabled, set_session_cookies
from webapp.services.mailer import configured_mailer


router = APIRouter(include_in_schema=False)


def _login_form_response(request: Request, template_name: str, **context):
    raw_csrf, csrf_hash = issue_login_csrf()
    response = templates.TemplateResponse(
        request=request,
        name=template_name,
        context={"page_title": "Entrar | Vitalis Ring", "login_csrf": raw_csrf, **context},
    )
    response.set_cookie(
        LOGIN_CSRF_COOKIE,
        csrf_hash,
        max_age=900,
        httponly=True,
        secure=secure_cookie_enabled(),
        samesite="lax",
        path="/login",
    )
    return response


def _complete_login(db: Session, user):
    new_session = create_session(db, user)
    if user.role == "technician":
        target = "/app/tecnico"
    else:
        target = "/app" if user.consented_at else "/app/consentimento"
    response = RedirectResponse(target, status_code=303)
    set_session_cookies(response, new_session)
    return response


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _login_form_response(request, "login.html")


@router.post("/login", response_class=HTMLResponse)
def request_login_link(
    request: Request,
    email: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_login_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    preview = request_login(
        db,
        email=email,
        ip=request.client.host if request.client else "unknown",
        public_base_url=os.environ["PUBLIC_BASE_URL"],
        mailer=configured_mailer(),
        demo_mode=env_flag("DEMO_MODE"),
    )
    return templates.TemplateResponse(
        request=request,
        name="login_requested.html",
        context={
            "page_title": "Confira seu e-mail | Vitalis Ring",
            "demo_preview": preview,
        },
    )


@router.get("/login/codigo", response_class=HTMLResponse)
def login_code_page(request: Request):
    return _login_form_response(request, "login_code.html", error=None)


@router.post("/login/codigo")
def login_with_code(
    request: Request,
    email: str = Form(""),
    code: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_login_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    user = consume_login_code(db, email, code.strip())
    if user is None:
        return _login_form_response(
            request,
            "login_code.html",
            error="Código inválido ou expirado. Solicite um novo acesso.",
        )
    return _complete_login(db, user)


@router.get("/login/token")
def login_with_magic_token(token: str, db: Session = Depends(get_db)):
    user = consume_magic_token(db, token)
    if user is None:
        return RedirectResponse("/login?erro=link-invalido", status_code=303)
    return _complete_login(db, user)
