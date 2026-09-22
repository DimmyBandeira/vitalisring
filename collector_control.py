"""Coordena o coletor contínuo e leituras pontuais sem concorrência BLE."""

import os
import subprocess
import sys
from pathlib import Path

import psutil


PROJECT_DIR = Path(__file__).resolve().parent
PID_FILE = PROJECT_DIR / "collector.pid"
ONCE_PID_FILE = PROJECT_DIR / "collector_once.pid"
REFRESH_LOCK = PROJECT_DIR / "refresh.lock"


def _collector_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
        process = psutil.Process(pid)
        if "collector.py" in " ".join(process.cmdline()):
            return pid
    except (OSError, ValueError, psutil.Error):
        pass
    path.unlink(missing_ok=True)
    return None


def get_running_pid() -> int | None:
    return _collector_pid(PID_FILE)


def get_once_pid() -> int | None:
    pid = _collector_pid(ONCE_PID_FILE)
    if pid is None:
        REFRESH_LOCK.unlink(missing_ok=True)
    return pid


def _popen(arguments: list[str]):
    options = {"cwd": PROJECT_DIR}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(arguments, **options)


def start_collector() -> int | None:
    if get_running_pid() or get_once_pid():
        return None
    process = _popen([sys.executable, "collector.py"])
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def stop_collector() -> None:
    pid = get_running_pid()
    if pid:
        try:
            psutil.Process(pid).terminate()
        except psutil.Error:
            pass
    PID_FILE.unlink(missing_ok=True)


def collect_once() -> int | None:
    if get_running_pid() or get_once_pid():
        return None
    try:
        descriptor = os.open(REFRESH_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
    except FileExistsError:
        return None
    try:
        process = _popen([sys.executable, "collector.py", "--once"])
        ONCE_PID_FILE.write_text(str(process.pid), encoding="utf-8")
        return process.pid
    except Exception:
        REFRESH_LOCK.unlink(missing_ok=True)
        raise
