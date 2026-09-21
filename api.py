"""
API central que recebe os dados do(s) coletor(es) de casa
e serve os dados pro dashboard.

Rodar com: uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

load_dotenv()

from models import Reading, SessionLocal, init_db

API_KEY = os.environ["API_KEY"]

app = FastAPI(title="Ring Health API")


@app.on_event("startup")
def startup():
    init_db()


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
        since = datetime.utcnow() - timedelta(hours=hours)
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
