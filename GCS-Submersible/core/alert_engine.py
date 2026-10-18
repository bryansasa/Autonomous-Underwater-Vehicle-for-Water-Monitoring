# -*- coding: utf-8 -*-
"""
Safety & Alert Engine for Submersible GCS
Monitors telemetry states against critical thresholds and fires safety warnings.
"""
from __future__ import annotations
import time
from typing import Dict, Any, Optional
from core.event_hook import EventHook


class AlertEngine:
    """
    Evaluates real-time telemetry against safety boundaries.
    Pure-Python implementation with zero GUI dependencies.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.last_telemetry_time = time.time()
        self.active_alerts: Dict[str, float] = {}  # alert_key -> timestamp
        self.alert_triggered = EventHook()  # (level, title, description)

        self._running = True
        self._check_thread = None

    def evaluate_telemetry(self, data: Dict[str, Any]):
        self.last_telemetry_time = time.time()

        batt_limits = self.config.get("battery_limits", {})
        soc = data.get("soc_kalman", data.get("soc", 100.0))
        depth = data.get("depth", 0.0)
        target_depth = data.get("target_depth", 0.0)
        error_depth = abs(depth - target_depth)

        # 1. Battery Alerts
        if soc <= batt_limits.get("soc_critical", 20.0):
            self._trigger("CRITICAL", "BATT_CRITICAL", f"Baterai Sangat Kritis ({soc:.1f}%)! Lakukan RTH/Surface.")
        elif soc <= batt_limits.get("soc_warning", 30.0):
            self._trigger("WARNING", "BATT_WARN", f"Baterai Menipis ({soc:.1f}%). EA-DSRA mengaktifkan penalti.")

        # 2. Maximum Depth Exceeded Alert
        if depth > 5.5:
            self._trigger("CRITICAL", "DEPTH_LIMIT", f"Kedalaman ({depth:.2f} m) melebihi batas operasional 5.0 m!")

        # 3. LMPC Tracking Error Alert
        if error_depth > 0.4 and target_depth > 0.1:
            self._trigger("WARNING", "LMPC_ERROR", f"Deviasi LMPC Heave ({error_depth:.2f} m) melebihi batas spesifikasi ±0.3 m.")

        # 4. Water Quality Anomaly Alerts
        do_val = data.get("do", 5.0)
        ph_val = data.get("ph", 7.0)

        if do_val < 2.0 and do_val > 0.01:
            self._trigger("WARNING", "DO_HYPOXIA", f"DO Air Kritis ({do_val:.2f} mg/L) - Indikasi Anoksia di Lapisan Ini!")
        if (ph_val < 6.0 or ph_val > 9.0) and ph_val > 0.1:
            self._trigger("WARNING", "PH_MUTU", f"pH ({ph_val:.2f}) di luar Baku Mutu PP 22/2021 (6.0 - 9.0).")

    def periodic_check(self):
        # Check connection heartbeat
        if time.time() - self.last_telemetry_time > 3.0:
            self._trigger("WARNING", "LINK_TIMEOUT", "Telemetri terputus > 3 detik. Memeriksa koneksi tether...")

    def _trigger(self, level: str, key: str, description: str):
        now = time.time()
        # Cooldown per alert key (10 seconds)
        if key not in self.active_alerts or (now - self.active_alerts[key]) > 10.0:
            self.active_alerts[key] = now
            self.alert_triggered.emit(level, key, description)
