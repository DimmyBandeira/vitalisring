"""Trava compartilhada do coletor e coordenação de processos BLE."""

from types import SimpleNamespace

import collector_control


def _paths(monkeypatch, tmp_path):
    monkeypatch.setattr(collector_control, "PID_FILE", tmp_path / "collector.pid")
    monkeypatch.setattr(collector_control, "ONCE_PID_FILE", tmp_path / "once.pid")
    monkeypatch.setattr(collector_control, "REFRESH_LOCK", tmp_path / "refresh.lock")


def test_double_collect_starts_only_one_process(monkeypatch, tmp_path):
    _paths(monkeypatch, tmp_path)
    monkeypatch.setattr(collector_control, "get_running_pid", lambda: None)
    monkeypatch.setattr(collector_control, "get_once_pid", lambda: None)
    calls = []
    monkeypatch.setattr(collector_control, "_popen", lambda args: calls.append(args) or SimpleNamespace(pid=4321))

    assert collector_control.collect_once() == 4321
    assert collector_control.collect_once() is None
    assert len(calls) == 1


def test_continuous_collector_blocks_one_shot(monkeypatch, tmp_path):
    _paths(monkeypatch, tmp_path)
    monkeypatch.setattr(collector_control, "get_running_pid", lambda: 1234)
    monkeypatch.setattr(collector_control, "_popen", lambda _args: (_ for _ in ()).throw(AssertionError("não deve iniciar")))

    assert collector_control.collect_once() is None
