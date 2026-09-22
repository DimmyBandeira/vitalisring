"""Limiares iniciais — validar clinicamente antes de uso real."""

MIN_SIGNAL_QUALITY = 0.70
THRESHOLDS = {
    "rest_brady": [(35, 0, "critical"), (40, 30, "alert"), (44, 60, "warn"), (49, 180, "info")],
    "sleep_brady": [(30, 1, "alert"), (34, 120, "info")],
    "rest_tachy": [(160, 60, "critical"), (140, 120, "alert"), (120, 300, "warn"), (100, 600, "info")],
    "spo2": [(85, 15, "critical"), (88, 30, "alert"), (90, 60, "warn"), (92, 300, "info")],
}
