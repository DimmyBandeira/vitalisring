"""Funções puras para a demonstração; não são regras clínicas validadas."""

from dataclasses import dataclass

from webapp.alerts.thresholds import MIN_SIGNAL_QUALITY, THRESHOLDS


@dataclass(frozen=True)
class RuleResult:
    level: str
    rule_key: str
    explanation: str


OK = RuleResult("ok", "none", "Nenhuma regra demonstrativa foi acionada.")


def _low_rule(value: float, duration: int, rules, prefix: str):
    for threshold, required, level in rules:
        if value <= threshold and duration >= required:
            return RuleResult(level, f"{prefix}_{level}", "A estimativa permaneceu abaixo do limiar demonstrativo pelo tempo configurado.")
    return None


def _high_rule(value: float, duration: int, rules, prefix: str):
    for threshold, required, level in rules:
        if value >= threshold and duration >= required:
            return RuleResult(level, f"{prefix}_{level}", "A estimativa permaneceu acima do limiar demonstrativo pelo tempo configurado.")
    return None


def evaluate(*, state: str, bpm: float, spo2: float, movement: str, duration_seconds: int, signal_quality: float, is_demo: bool = True) -> RuleResult:
    if not is_demo:
        return RuleResult("ok", "real_data_blocked", "Regras automáticas estão desligadas para dados reais.")
    if signal_quality < MIN_SIGNAL_QUALITY:
        return RuleResult("ok", "insufficient_quality", "Sem conclusão: qualidade sintética insuficiente.")
    if state == "rest" and movement == "low" and bpm >= 130 and spo2 <= 88:
        return RuleResult("critical", "combined_rest", "Duas estimativas sintéticas acionaram a prioridade máxima.")
    candidates = []
    spo2_result = _low_rule(spo2, duration_seconds, THRESHOLDS["spo2"], "spo2")
    if spo2_result:
        candidates.append(spo2_result)
    if state == "rest" and movement == "low":
        result = _low_rule(bpm, duration_seconds, THRESHOLDS["rest_brady"], "rest_brady")
        if result:
            candidates.append(result)
        result = _high_rule(bpm, duration_seconds, THRESHOLDS["rest_tachy"], "rest_tachy")
        if result:
            candidates.append(result)
    elif state == "sleep":
        result = _low_rule(bpm, duration_seconds, THRESHOLDS["sleep_brady"], "sleep_brady")
        if result:
            candidates.append(result)
    priority = {"ok": 0, "info": 1, "warn": 2, "alert": 3, "critical": 4}
    return max(candidates, key=lambda item: priority[item.level], default=OK)


def message_preview(name: str, level: str) -> dict[str, str]:
    messages = {
        "ok": f"{name}: nenhuma informação nova no momento.",
        "info": f"{name}: uma informação para você. Abra o app.",
        "warn": f"{name}: vale observar. Abra o app.",
        "alert": f"{name}: importante. Abra o app.",
        "critical": f"{name}: precisa de você agora. Abra o app. Em emergência, ligue 192.",
    }
    body = messages[level]
    return {"whatsapp": body, "email_subject": f"Atualização sobre {name}", "email_body": body}
