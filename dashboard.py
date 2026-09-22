"""
Dashboard Streamlit: mostra batimentos e SPO2 em tempo real + histórico.

Roda no MESMO servidor que a API (lê o banco direto, sem precisar de rede).
Rodar com: streamlit run dashboard.py --server.port 8501
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from collector_control import collect_once, get_running_pid, start_collector, stop_collector
from models import Reading, SessionLocal

PROJECT_DIR = Path(__file__).parent
STATUS_FILE = PROJECT_DIR / "ring_status.json"


def get_ring_status() -> dict | None:
    """Lê o último status de conexão BLE que o collector.py gravou."""
    if not STATUS_FILE.exists():
        return None
    try:
        return json.loads(STATUS_FILE.read_text())
    except (ValueError, OSError):
        return None


st.set_page_config(page_title="Painel do Anel", page_icon="💓", layout="wide")

DEVICE_ID = st.sidebar.text_input("Device ID", value="ring-01")
AUTO_REFRESH_SECONDS = st.sidebar.slider("Atualizar a cada (segundos)", 5, 120, 30)
HOURS = st.sidebar.slider("Janela de histórico (horas)", 1, 24 * 7, 24)

st.title("💓 Painel de Sinais Vitais — Anel Colmi")


def get_latest(device_id: str) -> dict:
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
                result[reading_type] = {"value": row.value, "timestamp": row.timestamp}
        return result
    finally:
        db.close()


def get_history(device_id: str, reading_type: str, hours: int) -> pd.DataFrame:
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        rows = (
            db.query(Reading)
            .filter(
                Reading.device_id == device_id,
                Reading.type == reading_type,
                Reading.timestamp >= since,
            )
            .order_by(Reading.timestamp.asc())
            .all()
        )
        return pd.DataFrame([{"timestamp": r.timestamp, "value": r.value} for r in rows])
    finally:
        db.close()


# --- Visão ao vivo ---
latest = get_latest(DEVICE_ID)
col1, col2, col3, col4 = st.columns(4)

with col1:
    if "heart_rate" in latest:
        age = (datetime.utcnow() - latest["heart_rate"]["timestamp"]).total_seconds()
        st.metric("Batimentos (BPM)", f"{latest['heart_rate']['value']:.0f}")
        st.caption(f"há {int(age)}s" if age < 300 else f"⚠️ dado antigo ({int(age/60)} min atrás)")
    else:
        st.metric("Batimentos (BPM)", "—")

with col2:
    if "spo2" in latest:
        age = (datetime.utcnow() - latest["spo2"]["timestamp"]).total_seconds()
        st.metric("SPO2 (%)", f"{latest['spo2']['value']:.0f}")
        st.caption(f"há {int(age)}s" if age < 300 else f"⚠️ dado antigo ({int(age/60)} min atrás)")
    else:
        st.metric("SPO2 (%)", "—")

with col3:
    if "battery" in latest:
        age = (datetime.utcnow() - latest["battery"]["timestamp"]).total_seconds()
        st.metric("Bateria (%)", f"{latest['battery']['value']:.0f}")
        st.caption(f"há {int(age)}s" if age < 300 else f"⚠️ dado antigo ({int(age/60)} min atrás)")
    else:
        st.metric("Bateria (%)", "—")

with col4:
    st.metric("Device ID", DEVICE_ID)

st.divider()

# --- Controle da coleta ---
st.subheader("Controle da coleta")
running_pid = get_running_pid()
ring_status = get_ring_status()

status1, status2 = st.columns(2)

with status1:
    if ring_status is None:
        st.info("⚪ Anel: sem tentativa de conexão registrada ainda")
    else:
        age = (datetime.utcnow() - datetime.fromisoformat(ring_status["checked_at"]).replace(tzinfo=None)).total_seconds()
        if ring_status["connected"]:
            st.success(f"🟢 Anel conectado (há {int(age)}s)")
        else:
            st.error(f"🔴 Anel desconectado (última tentativa há {int(age)}s)")
            if ring_status.get("error"):
                st.caption(ring_status["error"])

with status2:
    if running_pid:
        st.success(f"🟢 Coleta contínua rodando (PID {running_pid})")
    else:
        st.warning("🔴 Coleta contínua parada")

ctrl1, ctrl2 = st.columns(2)

with ctrl1:
    if running_pid:
        if st.button("⏹ Parar coleta contínua"):
            stop_collector()
            st.rerun()
    else:
        if st.button("▶ Iniciar coleta contínua"):
            start_collector()
            st.rerun()

with ctrl2:
    if st.button("📥 Coletar agora", disabled=bool(running_pid), help="Desabilitado enquanto a coleta contínua está rodando, pra não disputar o Bluetooth com o anel"):
        collect_once()
        st.toast("Coleta manual iniciada — a leitura do anel demora ~1 min, deve aparecer no próximo auto-refresh")

st.divider()

# --- Histórico ---
tab1, tab2, tab3 = st.tabs(["Batimentos", "SPO2", "Bateria"])

with tab1:
    df_hr = get_history(DEVICE_ID, "heart_rate", HOURS)
    df_hr_log = get_history(DEVICE_ID, "heart_rate_log", HOURS)
    combined = pd.concat([df_hr, df_hr_log]).sort_values("timestamp") if not df_hr_log.empty else df_hr
    if not combined.empty:
        st.line_chart(combined.set_index("timestamp")["value"], y_label="BPM")
    else:
        st.info("Ainda sem dados de batimentos nesse período.")

with tab2:
    df_spo2 = get_history(DEVICE_ID, "spo2", HOURS)
    if not df_spo2.empty:
        st.line_chart(df_spo2.set_index("timestamp")["value"], y_label="SPO2 %")
    else:
        st.info("Ainda sem dados de SPO2 nesse período (apenas leitura pontual em tempo real é suportada pela lib atualmente).")

with tab3:
    df_battery = get_history(DEVICE_ID, "battery", HOURS)
    if not df_battery.empty:
        st.line_chart(df_battery.set_index("timestamp")["value"], y_label="Bateria %")
    else:
        st.info("Ainda sem dados de bateria nesse período.")

st.caption(f"Atualizando a cada {AUTO_REFRESH_SECONDS}s...")
time.sleep(AUTO_REFRESH_SECONDS)
st.rerun()
