"""Tabela de limites das regras exclusivamente demonstrativas."""

import re

import pytest

from webapp.alerts.rules import evaluate, message_preview


@pytest.mark.parametrize(
    ("state", "bpm", "spo2", "duration", "expected"),
    [
        ("rest", 49, 97, 179, "ok"),
        ("rest", 49, 97, 180, "info"),
        ("rest", 40, 97, 30, "alert"),
        ("rest", 35, 97, 0, "critical"),
        ("rest", 121, 97, 299, "ok"),
        ("rest", 121, 97, 300, "warn"),
        ("rest", 160, 97, 60, "critical"),
        ("sleep", 34, 97, 120, "info"),
        ("sleep", 30, 97, 1, "alert"),
        ("rest", 72, 92, 300, "info"),
        ("rest", 72, 88, 30, "alert"),
        ("rest", 72, 85, 15, "critical"),
        ("rest", 130, 88, 60, "critical"),
    ],
)
def test_rule_table(state, bpm, spo2, duration, expected):
    result = evaluate(state=state, bpm=bpm, spo2=spo2, movement="low", duration_seconds=duration, signal_quality=0.95)
    assert result.level == expected


def test_low_quality_and_real_device_do_not_reach_health_conclusion():
    low_quality = evaluate(state="rest", bpm=30, spo2=80, movement="low", duration_seconds=600, signal_quality=0.2)
    real = evaluate(state="rest", bpm=30, spo2=80, movement="low", duration_seconds=600, signal_quality=1, is_demo=False)
    assert low_quality.rule_key == "insufficient_quality"
    assert real.rule_key == "real_data_blocked"
    assert low_quality.level == real.level == "ok"


@pytest.mark.parametrize("level", ["ok", "info", "warn", "alert", "critical"])
def test_external_previews_contain_no_health_numbers(level):
    preview = message_preview("Maria", level)
    content = " ".join(preview.values()).replace("192", "")
    assert not re.search(r"\b(?:3[0-9]|[4-9][0-9]|1[0-9]{2})\b", content)
