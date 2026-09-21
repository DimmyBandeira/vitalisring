"""
Coletor do anel Colmi R02 -> API central.

Roda em CASA, perto do anel (Bluetooth tem alcance curto).
A cada RT_INTERVAL_SECONDS ele:
  1. Liga no anel via BLE
  2. Pega uma leitura de batimentos (heart rate) em tempo real
  3. Pega uma leitura de SPO2 em tempo real
  4. Envia os dois pra API central via HTTPS

A cada HISTORY_INTERVAL_SECONDS ele também sincroniza o log histórico
de batimentos que o anel guardou sozinho (medição periódica automática).

Se a API estiver fora do ar, as leituras ficam guardadas num arquivo
local (buffer.jsonl) e são reenviadas na próxima tentativa bem-sucedida.
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from colmi_r02_client.client import Client
from colmi_r02_client import hr

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("collector")

# ---- Configuração (pode vir de variáveis de ambiente) ----
RING_ADDRESS = os.environ["RING_ADDRESS"]  # ex: 70:CB:0D:D0:34:1C, ache com `colmi_r02_util scan`
API_URL = os.environ.get("API_URL", "http://localhost:8000")
API_KEY = os.environ["API_KEY"]
DEVICE_ID = os.environ.get("DEVICE_ID", "ring-01")

RT_INTERVAL_SECONDS = int(os.environ.get("RT_INTERVAL_SECONDS", "60"))
HISTORY_INTERVAL_SECONDS = int(os.environ.get("HISTORY_INTERVAL_SECONDS", "1800"))  # 30 min

BUFFER_FILE = Path(os.environ.get("BUFFER_FILE", "buffer.jsonl"))
STATUS_FILE = Path(os.environ.get("STATUS_FILE", "ring_status.json"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(connected: bool, error: str | None = None) -> None:
    """Grava o status de conexão com o anel num arquivo local, pro dashboard ler."""
    STATUS_FILE.write_text(json.dumps({
        "connected": connected,
        "checked_at": now_iso(),
        "error": error,
    }))


async def send_readings(client: httpx.AsyncClient, readings: list[dict]) -> bool:
    """Tenta enviar uma lista de leituras pra API. Retorna True se deu certo."""
    if not readings:
        return True
    try:
        resp = await client.post(
            f"{API_URL}/readings/bulk",
            json={"readings": readings},
            headers={"X-API-Key": API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info(f"Enviadas {len(readings)} leituras com sucesso")
        return True
    except Exception as e:
        logger.warning(f"Falha ao enviar pra API ({e}), guardando no buffer local")
        return False


def buffer_readings(readings: list[dict]) -> None:
    with BUFFER_FILE.open("a") as f:
        for r in readings:
            f.write(json.dumps(r) + "\n")


async def flush_buffer(client: httpx.AsyncClient) -> None:
    """Tenta reenviar o que ficou acumulado localmente."""
    if not BUFFER_FILE.exists():
        return
    lines = BUFFER_FILE.read_text().splitlines()
    if not lines:
        return
    readings = [json.loads(line) for line in lines if line.strip()]
    ok = await send_readings(client, readings)
    if ok:
        BUFFER_FILE.unlink()
        logger.info(f"Buffer local ({len(readings)} leituras) reenviado e limpo")


async def read_realtime(ring: Client) -> list[dict]:
    """Lê BPM e SPO2 em tempo real do anel."""
    readings = []
    ts = now_iso()

    try:
        hr_values = await ring.get_realtime_heart_rate()
        if hr_values:
            # descarta zeros/ruído, usa a média das leituras válidas
            valid = [v for v in hr_values if v > 0]
            if valid:
                bpm = round(sum(valid) / len(valid))
                readings.append({
                    "device_id": DEVICE_ID,
                    "type": "heart_rate",
                    "value": bpm,
                    "timestamp": ts,
                })
                logger.info(f"BPM: {bpm} (amostras: {hr_values})")
    except Exception as e:
        logger.warning(f"Erro lendo heart rate: {e}")

    try:
        spo2_values = await ring.get_realtime_spo2()
        if spo2_values:
            valid = [v for v in spo2_values if v > 0]
            if valid:
                spo2 = round(sum(valid) / len(valid))
                readings.append({
                    "device_id": DEVICE_ID,
                    "type": "spo2",
                    "value": spo2,
                    "timestamp": ts,
                })
                logger.info(f"SPO2: {spo2}% (amostras: {spo2_values})")
    except Exception as e:
        logger.warning(f"Erro lendo SPO2: {e}")

    return readings


async def read_battery(ring: Client) -> list[dict]:
    """Lê nível de bateria do anel."""
    readings = []
    try:
        info = await ring.get_battery()
        readings.append({
            "device_id": DEVICE_ID,
            "type": "battery",
            "value": info.battery_level,
            "timestamp": now_iso(),
        })
        logger.info(f"Bateria: {info.battery_level}% ({'carregando' if info.charging else 'não carregando'})")
    except Exception as e:
        logger.warning(f"Erro lendo bateria: {e}")
    return readings


async def read_heart_rate_history(ring: Client) -> list[dict]:
    """Sincroniza o log histórico de batimentos que o anel guardou sozinho hoje."""
    readings = []
    try:
        today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        log = await ring.get_heart_rate_log(today_midnight)
        if isinstance(log, hr.NoData):
            logger.info("Sem log histórico disponível ainda")
            return readings

        for value, ts in log.heart_rates_with_times():
            if value > 0:  # 0 = sem medição naquele intervalo de 5 min
                readings.append({
                    "device_id": DEVICE_ID,
                    "type": "heart_rate_log",
                    "value": value,
                    "timestamp": ts.replace(tzinfo=timezone.utc).isoformat(),
                })
        logger.info(f"Log histórico: {len(readings)} pontos coletados")
    except Exception as e:
        logger.warning(f"Erro lendo log histórico: {e}")

    return readings


async def collect_cycle(http_client: httpx.AsyncClient, sync_history: bool) -> None:
    """Um ciclo completo: conecta no anel, lê tudo, envia pra API, tenta esvaziar buffer."""
    try:
        async with Client(RING_ADDRESS) as ring:
            write_status(connected=True)
            readings = await read_realtime(ring)
            readings += await read_battery(ring)
            if sync_history:
                readings += await read_heart_rate_history(ring)

        if readings:
            ok = await send_readings(http_client, readings)
            if not ok:
                buffer_readings(readings)

        await flush_buffer(http_client)

    except Exception as e:
        logger.error(f"Erro no ciclo de coleta (anel desconectado?): {e}")
        write_status(connected=False, error=str(e))


async def run_once() -> None:
    """Faz uma única leitura (sem histórico) e sai. Usado pelo botão 'Coletar agora' do dashboard."""
    async with httpx.AsyncClient() as http_client:
        await collect_cycle(http_client, sync_history=False)


async def run_loop() -> None:
    last_history_sync = 0.0

    async with httpx.AsyncClient() as http_client:
        while True:
            loop_start = asyncio.get_event_loop().time()
            sync_history = loop_start - last_history_sync > HISTORY_INTERVAL_SECONDS

            await collect_cycle(http_client, sync_history=sync_history)

            if sync_history:
                last_history_sync = loop_start

            await asyncio.sleep(RT_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Faz uma única leitura e sai, em vez de rodar em loop")
    args = parser.parse_args()

    asyncio.run(run_once() if args.once else run_loop())
