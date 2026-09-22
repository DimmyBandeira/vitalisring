"""Console profissional com escopo por vínculo, consentimento e auditoria."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from models import Reading
from webapp.models_app import Alert, CareLink, Device
from webapp.routes.common import templates
from webapp.security.audit import record_patient_access
from webapp.security.authorization import authorize_patient
from webapp.security.sessions import CSRF_COOKIE_NAME, authenticated_context, get_db
from webapp.services.family_dashboard import STATUS_PRESENTATION, local_datetime, relative_time

router = APIRouter(include_in_schema=False)
PROFESSIONAL_ROLES = {"doctor", "institution", "owner"}
PRIORITY = {"critical": 0, "alert": 1, "warn": 2, "info": 3, "ok": 4}


def _professional(request: Request, db: Session):
    try:
        session, user = authenticated_context(request, db)
    except HTTPException:
        return None, RedirectResponse("/profissional/login", status_code=303)
    if user.role not in PROFESSIONAL_ROLES:
        raise HTTPException(status_code=403, detail="Acesso profissional não autorizado")
    return (session, user), None


def _patient_status(db: Session, patient_id: str):
    alert = db.query(Alert).filter(Alert.patient_id == patient_id, Alert.status == "open").order_by(Alert.created_at.desc()).first()
    key = alert.level if alert and alert.level in STATUS_PRESENTATION else "ok"
    return key, STATUS_PRESENTATION[key][0]


@router.get("/app/medico", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    context, redirect = _professional(request, db)
    if redirect:
        return redirect
    _session, user = context
    links = db.query(CareLink).filter(CareLink.user_id == user.id, CareLink.is_active.is_(True)).all()
    rows = []
    for link in links:
        try:
            patient = authorize_patient(db, user, link.patient_id)
        except HTTPException:
            continue
        key, label = _patient_status(db, patient.id)
        device = db.query(Device).filter(Device.patient_id == patient.id).first()
        latest = db.query(Reading).filter(Reading.device_id == device.device_id).order_by(Reading.timestamp.desc()).first() if device else None
        rows.append({"patient": patient, "status_key": key, "status_label": label, "latest": relative_time(latest.timestamp if latest else None)})
    rows.sort(key=lambda row: (PRIORITY[row["status_key"]], row["patient"].display_name))
    return templates.TemplateResponse(request=request, name="doctor_home.html", context={"page_title": "Console médico | Vitalis Ring", "current_user": user, "patients": rows})


@router.get("/app/medico/pacientes/{patient_id}", response_class=HTMLResponse)
def detail(patient_id: str, request: Request, db: Session = Depends(get_db)):
    context, redirect = _professional(request, db)
    if redirect:
        return redirect
    _session, user = context
    patient = authorize_patient(db, user, patient_id)
    record_patient_access(db, user=user, patient_id=patient.id, purpose="clinical_console", request_id=getattr(request.state, "request_id", None), ip=request.client.host if request.client else None)
    device = db.query(Device).filter(Device.patient_id == patient.id).first()
    readings = db.query(Reading).filter(Reading.device_id == device.device_id).order_by(Reading.timestamp.desc()).limit(30).all() if device else []
    heart = [item for item in reversed(readings) if item.type == "heart_rate"]
    points = " ".join(f"{10 + index * (280 / max(1, len(heart) - 1)):.1f},{90 - min(70, max(0, item.value - 40))}" for index, item in enumerate(heart))
    key, label = _patient_status(db, patient.id)
    return templates.TemplateResponse(request=request, name="doctor_patient.html", context={"page_title": f"{patient.display_name} | Vitalis Ring", "patient": patient, "device": device, "readings": readings, "points": points, "status_key": key, "status_label": label, "local_datetime": local_datetime, "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, "")})
