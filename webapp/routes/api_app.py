"""Endpoints internos da área logada."""

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from webapp.security.audit import record_patient_access
from webapp.security.authorization import authorize_patient
from webapp.security.csrf import validate_csrf
from webapp.security.sessions import authenticated_context, get_db, session_secret


router = APIRouter(prefix="/app/api", tags=["app"], include_in_schema=False)


def _summary_response(patient):
    return {
        "patient_id": patient.id,
        "display_name": patient.display_name,
        "is_demo": patient.is_demo,
    }


def _require_csrf(request: Request, csrf_hash: str) -> None:
    public_base_url = os.environ.get("PUBLIC_BASE_URL", "")
    if not public_base_url or not validate_csrf(
        supplied_token=request.headers.get("X-CSRF-Token"),
        expected_hash=csrf_hash,
        origin=request.headers.get("Origin"),
        allowed_origins={public_base_url},
        secret=session_secret(),
    ):
        raise HTTPException(status_code=403, detail="Requisição inválida")


@router.get("/patients/{patient_id}/summary")
def patient_summary(patient_id: str, request: Request, db: Session = Depends(get_db)):
    _session, user = authenticated_context(request, db)
    patient = authorize_patient(db, user, patient_id)
    record_patient_access(
        db,
        user=user,
        patient_id=patient.id,
        purpose="patient_summary",
        request_id=request.headers.get("X-Request-ID"),
        ip=request.client.host if request.client else None,
    )
    return _summary_response(patient)


@router.post("/patients/select")
def select_patient(
    request: Request,
    patient_id: str = Form(...),
    db: Session = Depends(get_db),
):
    session, user = authenticated_context(request, db)
    _require_csrf(request, session.csrf_hash)
    patient = authorize_patient(db, user, patient_id)
    record_patient_access(
        db,
        user=user,
        patient_id=patient.id,
        purpose="select_patient",
        request_id=request.headers.get("X-Request-ID"),
        ip=request.client.host if request.client else None,
    )
    return _summary_response(patient)
