"""Simulador profissional explicitamente sintético."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from webapp.alerts.rules import evaluate, message_preview
from webapp.routes.common import templates
from webapp.routes.medico import _professional
from webapp.security.csrf import validate_session_csrf
from webapp.security.sessions import CSRF_COOKIE_NAME, get_db

router = APIRouter(include_in_schema=False)


def _render(request, user, result=None, preview=None):
    return templates.TemplateResponse(request=request, name="simulator.html", context={"page_title": "Simulador | Vitalis Ring", "current_user": user, "result": result, "preview": preview, "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, "")})


@router.get("/app/simulador", response_class=HTMLResponse)
def page(request: Request, db: Session = Depends(get_db)):
    context, redirect = _professional(request, db)
    if redirect:
        return redirect
    return _render(request, context[1])


@router.post("/app/simulador", response_class=HTMLResponse)
def simulate(request: Request, state: str = Form("rest"), bpm: float = Form(...), spo2: float = Form(...), movement: str = Form("low"), duration_seconds: int = Form(...), signal_quality: float = Form(...), patient_name: str = Form("Maria"), csrf_token: str = Form(""), db: Session = Depends(get_db)):
    context, redirect = _professional(request, db)
    if redirect:
        return redirect
    session, user = context
    if not validate_session_csrf(request, csrf_token, session.csrf_hash):
        raise HTTPException(status_code=403, detail="Requisição inválida")
    result = evaluate(state=state, bpm=bpm, spo2=spo2, movement=movement, duration_seconds=duration_seconds, signal_quality=signal_quality, is_demo=True)
    return _render(request, user, result, message_preview(patient_name.strip() or "Pessoa monitorada", result.level))
