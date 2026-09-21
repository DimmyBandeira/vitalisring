"""Endpoints internos da área logada."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from webapp.security.audit import record_patient_access
from webapp.security.authorization import authorize_patient
from webapp.security.sessions import authenticated_context, get_db


router = APIRouter(prefix="/app/api", tags=["app"], include_in_schema=False)


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
    return {
        "patient_id": patient.id,
        "display_name": patient.display_name,
        "is_demo": patient.is_demo,
    }
