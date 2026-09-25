"""Login profissional com senha Argon2 e segundo fator obrigatório."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from webapp.routes.common import templates
from webapp.security.csrf import LOGIN_CSRF_COOKIE, issue_login_csrf, validate_login_csrf
from webapp.security.professional_auth import (
    consume_challenge,
    create_recovery_codes,
    ensure_totp,
    fail_challenge,
    issue_challenge,
    load_challenge,
    mfa_is_configured,
    totp_qr_svg,
    verify_password,
    verify_second_factor,
    verify_totp_code,
)
from webapp.security.ratelimit import consume
from webapp.security.sessions import create_session, get_db, secure_cookie_enabled, session_secret, set_session_cookies
from webapp.models_app import User


router = APIRouter(include_in_schema=False)
CHALLENGE_COOKIE = "vr_professional_challenge"


def _form(request: Request, template: str, **context):
    raw, hashed = issue_login_csrf()
    response = templates.TemplateResponse(
        request=request,
        name=template,
        context={"page_title": "Acesso profissional | Vitalis Ring", "login_csrf": raw, **context},
    )
    response.set_cookie(LOGIN_CSRF_COOKIE, hashed, max_age=900, httponly=True, secure=secure_cookie_enabled(), samesite="lax", path="/profissional")
    return response


def _set_challenge(response, token: str):
    response.set_cookie(CHALLENGE_COOKIE, token, max_age=300, httponly=True, secure=secure_cookie_enabled(), samesite="lax", path="/profissional")


def _finish(request: Request, db: Session, user: User, challenge, recovery_codes=None):
    consume_challenge(db, challenge)
    session = create_session(db, user)
    if recovery_codes:
        response = templates.TemplateResponse(
            request=request,
            name="professional_recovery.html",
            context={"page_title": "Códigos de recuperação | Vitalis Ring", "codes": recovery_codes},
        )
    else:
        target = "/app/tecnico" if user.role in {"technician", "owner"} else "/app/medico"
        response = RedirectResponse(target, status_code=303)
    set_session_cookies(response, session)
    response.delete_cookie(CHALLENGE_COOKIE, path="/profissional")
    return response


@router.get("/profissional/login", response_class=HTMLResponse)
def page(request: Request):
    return _form(request, "professional_login.html", error=None)


@router.post("/profissional/login")
def password_step(request: Request, email: str = Form(""), password: str = Form(""), csrf_token: str = Form(""), db: Session = Depends(get_db)):
    if not validate_login_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    normalized_email = email.strip().casefold()
    secret = session_secret()
    window = timedelta(minutes=15)
    ip = request.client.host if request.client else "unknown"
    allowed = consume(db, scope="professional-login-ip", identifier=ip, secret=secret, limit=50, window=window)
    allowed = consume(db, scope="professional-login-email", identifier=normalized_email, secret=secret, limit=10, window=window) and allowed
    user = db.query(User).filter(User.email == normalized_email, User.is_active.is_(True)).first()
    if not allowed or user is None or user.role not in {"doctor", "institution", "technician", "owner"} or not verify_password(user.password_hash, password):
        return _form(request, "professional_login.html", error="Credenciais inválidas.")
    challenge = issue_challenge(db, user)
    target = "/profissional/mfa" if mfa_is_configured(db, user) else "/profissional/configurar-mfa"
    response = RedirectResponse(target, status_code=303)
    _set_challenge(response, challenge.token)
    return response


@router.get("/profissional/configurar-mfa", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    loaded = load_challenge(db, request.cookies.get(CHALLENGE_COOKIE))
    if loaded is None:
        return RedirectResponse("/profissional/login", status_code=303)
    _challenge, user = loaded
    secret = ensure_totp(user, db)
    return _form(request, "professional_setup_mfa.html", qr_svg=totp_qr_svg(user, secret), secret=secret, error=None)


@router.post("/profissional/configurar-mfa")
def setup_confirm(request: Request, code: str = Form(""), csrf_token: str = Form(""), db: Session = Depends(get_db)):
    if not validate_login_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    loaded = load_challenge(db, request.cookies.get(CHALLENGE_COOKIE))
    if loaded is None:
        return RedirectResponse("/profissional/login", status_code=303)
    challenge, user = loaded
    if not verify_totp_code(user, code):
        fail_challenge(db, challenge)
        secret = ensure_totp(user, db)
        return _form(request, "professional_setup_mfa.html", qr_svg=totp_qr_svg(user, secret), secret=secret, error="Código inválido.")
    return _finish(request, db, user, challenge, create_recovery_codes(db, user))


@router.get("/profissional/mfa", response_class=HTMLResponse)
def mfa_page(request: Request, db: Session = Depends(get_db)):
    if load_challenge(db, request.cookies.get(CHALLENGE_COOKIE)) is None:
        return RedirectResponse("/profissional/login", status_code=303)
    return _form(request, "professional_mfa.html", error=None)


@router.post("/profissional/mfa")
def mfa_confirm(request: Request, code: str = Form(""), csrf_token: str = Form(""), db: Session = Depends(get_db)):
    if not validate_login_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    loaded = load_challenge(db, request.cookies.get(CHALLENGE_COOKIE))
    if loaded is None:
        return RedirectResponse("/profissional/login", status_code=303)
    challenge, user = loaded
    if not verify_second_factor(db, user, code):
        fail_challenge(db, challenge)
        return _form(request, "professional_mfa.html", error="Código inválido.")
    return _finish(request, db, user, challenge)
