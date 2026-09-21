"""Área de implantação usada pelo técnico da Vitalis."""

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from webapp.models_app import Device
from webapp.routes.common import templates
from webapp.security.config import env_flag
from webapp.security.csrf import validate_session_csrf
from webapp.security.magic_login import request_login
from webapp.security.sessions import CSRF_COOKIE_NAME, authenticated_context, get_db
from webapp.services.mailer import configured_mailer
from webapp.services.onboarding import (
    OnboardingError,
    activate_synthetic_device,
    create_customer_onboarding,
)


router = APIRouter(prefix="/app/tecnico", include_in_schema=False)


def technical_context(request: Request, db: Session):
    session, user = authenticated_context(request, db)
    if user.role not in {"technician", "owner"}:
        raise HTTPException(status_code=403, detail="Acesso técnico não autorizado")
    return session, user


@router.get("", response_class=HTMLResponse)
def technician_home(request: Request, db: Session = Depends(get_db)):
    _session, user = technical_context(request, db)
    query = db.query(Device).order_by(Device.created_at.desc())
    if user.role == "technician":
        query = query.filter(Device.registered_by == user.id)
    return templates.TemplateResponse(
        request=request,
        name="technician_home.html",
        context={
            "page_title": "Implantações | Vitalis Ring",
            "current_user": user,
            "devices": query.all(),
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def new_customer_page(request: Request, db: Session = Depends(get_db)):
    _session, user = technical_context(request, db)
    return templates.TemplateResponse(
        request=request,
        name="technician_onboarding.html",
        context={
            "page_title": "Novo cliente | Vitalis Ring",
            "current_user": user,
            "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
            "error": None,
        },
    )


@router.post("/novo", response_class=HTMLResponse)
def create_customer(
    request: Request,
    customer_name: str = Form(""),
    customer_email: str = Form(""),
    patient_name: str = Form(""),
    device_id: str = Form(""),
    serial_number: str = Form(""),
    source: str = Form("synthetic"),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    session, user = technical_context(request, db)
    if not validate_session_csrf(request, csrf_token, session.csrf_hash):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    try:
        result = create_customer_onboarding(
            db,
            technician=user,
            customer_name=customer_name,
            customer_email=customer_email,
            patient_name=patient_name,
            device_id=device_id,
            serial_number=serial_number,
            source=source,
        )
    except OnboardingError as exc:
        return templates.TemplateResponse(
            request=request,
            name="technician_onboarding.html",
            context={
                "page_title": "Novo cliente | Vitalis Ring",
                "current_user": user,
                "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
                "error": str(exc),
            },
            status_code=409,
        )
    preview = request_login(
        db,
        email=result.customer.email,
        ip=request.client.host if request.client else "unknown",
        public_base_url=os.environ["PUBLIC_BASE_URL"],
        mailer=configured_mailer(),
        demo_mode=env_flag("DEMO_MODE"),
    )
    return templates.TemplateResponse(
        request=request,
        name="technician_created.html",
        context={
            "page_title": "Cliente cadastrado | Vitalis Ring",
            "current_user": user,
            "customer": result.customer,
            "patient": result.patient,
            "device": result.device,
            "demo_preview": preview,
            "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
        },
        status_code=201,
    )


@router.get("/dispositivos/{device_id}", response_class=HTMLResponse)
def device_detail(device_id: str, request: Request, db: Session = Depends(get_db)):
    _session, user = technical_context(request, db)
    query = db.query(Device).filter(Device.id == device_id)
    if user.role == "technician":
        query = query.filter(Device.registered_by == user.id)
    device = query.first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    return templates.TemplateResponse(
        request=request,
        name="technician_device.html",
        context={
            "page_title": "Ativação do dispositivo | Vitalis Ring",
            "current_user": user,
            "device": device,
            "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
        },
    )


@router.post("/dispositivos/{device_id}/ativar-demo")
def activate_demo_device(
    device_id: str,
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    session, user = technical_context(request, db)
    if not validate_session_csrf(request, csrf_token, session.csrf_hash):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    try:
        activate_synthetic_device(db, device=device, technician=user)
    except OnboardingError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return RedirectResponse(f"/app/tecnico/dispositivos/{device.id}", status_code=303)
