"""Entrada autenticada, consentimento inicial e logout."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from models import utcnow_naive
from webapp.routes.common import templates
from webapp.models_app import Device, RefreshRequest
from webapp.security.authorization import authorize_patient
from webapp.security.csrf import validate_session_csrf
from webapp.security.sessions import (
    CSRF_COOKIE_NAME,
    authenticated_context,
    clear_session_cookies,
    get_db,
    revoke_session,
)
from webapp.services.family_dashboard import load_family_dashboard
from webapp.services.onboarding import refresh_synthetic_device


CONSENT_VERSION = "2026-09-v1"
router = APIRouter(include_in_schema=False)


def _context_or_redirect(request: Request, db: Session):
    try:
        return authenticated_context(request, db), None
    except HTTPException:
        return None, RedirectResponse("/login", status_code=303)


@router.get("/app", response_class=HTMLResponse)
def app_home(request: Request, db: Session = Depends(get_db)):
    context, redirect = _context_or_redirect(request, db)
    if redirect:
        return redirect
    _session, user = context
    if not user.consented_at:
        return RedirectResponse("/app/consentimento", status_code=303)
    dashboard = load_family_dashboard(db, user)
    return templates.TemplateResponse(
        request=request,
        name="family_dashboard.html",
        context={
            "page_title": "Área Vitalis | Vitalis Ring",
            "current_user": user,
            "dashboard": dashboard,
            "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
        },
    )


@router.post("/app/pacientes/{patient_id}/atualizar")
def refresh_patient(
    patient_id: str,
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    session, user = authenticated_context(request, db)
    if not validate_session_csrf(request, csrf_token, session.csrf_hash):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    patient = authorize_patient(db, user, patient_id)
    device = db.query(Device).filter(Device.patient_id == patient.id).first()
    if device is None:
        raise HTTPException(status_code=409, detail="Paciente sem dispositivo")
    now = utcnow_naive()
    pending = (
        db.query(RefreshRequest)
        .filter(
            RefreshRequest.patient_id == patient.id,
            RefreshRequest.status == "pending",
            RefreshRequest.expires_at > now,
        )
        .first()
    )
    if pending is None:
        pending = RefreshRequest(
            patient_id=patient.id,
            device_id=device.id,
            requested_by=user.id,
            status="pending",
            requested_at=now,
            expires_at=now + timedelta(seconds=120),
        )
        db.add(pending)
        db.commit()
    if device.source == "synthetic" and pending.status == "pending":
        # O gerador definitivo e o polling HTMX entram na Fase 8. Aqui a leitura
        # imediata torna o fluxo familiar testável sem alegar acesso ao BLE.
        refresh_synthetic_device(db, device=device)
        pending.status = "completed"
        pending.completed_at = utcnow_naive()
        db.commit()
    return RedirectResponse("/app", status_code=303)


@router.get("/app/consentimento", response_class=HTMLResponse)
def consent_page(request: Request, db: Session = Depends(get_db)):
    context, redirect = _context_or_redirect(request, db)
    if redirect:
        return redirect
    _session, user = context
    if user.consented_at:
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="consent.html",
        context={
            "page_title": "Consentimento | Vitalis Ring",
            "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
        },
    )


@router.post("/app/consentimento")
def accept_consent(
    request: Request,
    accepted: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    session, user = authenticated_context(request, db)
    if not validate_session_csrf(request, csrf_token, session.csrf_hash):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    if accepted != "yes":
        raise HTTPException(status_code=422, detail="Consentimento obrigatório")
    user.consent_version = CONSENT_VERSION
    user.consented_at = utcnow_naive()
    db.commit()
    return RedirectResponse("/app", status_code=303)


@router.get("/logout", response_class=HTMLResponse)
def logout_page(request: Request, db: Session = Depends(get_db)):
    context, redirect = _context_or_redirect(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request=request,
        name="logout.html",
        context={
            "page_title": "Sair | Vitalis Ring",
            "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
        },
    )


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    session, _user = authenticated_context(request, db)
    if not validate_session_csrf(request, csrf_token, session.csrf_hash):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    revoke_session(db, session)
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookies(response)
    return response
