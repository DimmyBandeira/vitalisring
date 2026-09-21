"""
API central que recebe os dados do(s) coletor(es) de casa
e serve os dados pro dashboard.

Rodar com: uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from models import Reading, SessionLocal, init_db
from webapp.security.config import env_flag, validate_public_exposure
from webapp.security.headers import install_security_headers
from webapp.routes.pages import router as web_pages_router
from webapp.routes.api_app import router as app_api_router

API_KEY = os.environ.get("API_KEY", "")
PUBLIC_EXPOSURE = env_flag("PUBLIC_EXPOSURE")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
validate_public_exposure(API_KEY, PUBLIC_EXPOSURE, SESSION_SECRET)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Ring Health API",
    docs_url=None if PUBLIC_EXPOSURE else "/docs",
    redoc_url=None if PUBLIC_EXPOSURE else "/redoc",
    openapi_url=None if PUBLIC_EXPOSURE else "/openapi.json",
    lifespan=lifespan,
)
install_security_headers(app, PUBLIC_EXPOSURE)


def check_api_key(x_api_key: str | None):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")


class ReadingIn(BaseModel):
    device_id: str
    type: Literal["heart_rate", "spo2", "heart_rate_log", "battery"]
    value: float
    timestamp: datetime


class BulkReadingsIn(BaseModel):
    readings: list[ReadingIn]


@app.post("/readings/bulk")
def post_readings(payload: BulkReadingsIn, x_api_key: str | None = Header(default=None)):
    check_api_key(x_api_key)
    db = SessionLocal()
    try:
        for r in payload.readings:
            db.add(Reading(
                device_id=r.device_id,
                type=r.type,
                value=r.value,
                timestamp=r.timestamp.replace(tzinfo=None),
            ))
        db.commit()
        return {"status": "ok", "count": len(payload.readings)}
    finally:
        db.close()


@app.get("/readings/latest")
def get_latest(
    device_id: str = Query(default="ring-01"),
    x_api_key: str | None = Header(default=None),
):
    """Última leitura de cada tipo (pra visão 'ao vivo' do dashboard)."""
    check_api_key(x_api_key)
    db = SessionLocal()
    try:
        result = {}
        for reading_type in ["heart_rate", "spo2", "battery"]:
            row = (
                db.query(Reading)
                .filter(Reading.device_id == device_id, Reading.type == reading_type)
                .order_by(Reading.timestamp.desc())
                .first()
            )
            if row:
                result[reading_type] = {"value": row.value, "timestamp": row.timestamp.isoformat()}
        return result
    finally:
        db.close()


@app.get("/readings/history")
def get_history(
    device_id: str = Query(default="ring-01"),
    type: str = Query(default="heart_rate"),
    hours: int = Query(default=24, le=24 * 30),
    x_api_key: str | None = Header(default=None),
):
    """Histórico de um tipo de leitura nas últimas N horas."""
    check_api_key(x_api_key)
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        rows = (
            db.query(Reading)
            .filter(Reading.device_id == device_id, Reading.type == type, Reading.timestamp >= since)
            .order_by(Reading.timestamp.asc())
            .all()
        )
        return [{"value": r.value, "timestamp": r.timestamp.isoformat()} for r in rows]
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


# Rotas e montagens HTML ficam por último para que o site na raiz nunca capture
# endpoints da API nem páginas da aplicação.
app.include_router(web_pages_router)
app.include_router(app_api_router)
app.mount("/static", StaticFiles(directory="static"), name="app-static")
app.mount("/design", StaticFiles(directory="site/design"), name="design-system")
app.mount("/", StaticFiles(directory="site/dist", html=True), name="public-site")
