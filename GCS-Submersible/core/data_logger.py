# -*- coding: utf-8 -*-
"""
Data Logger Module for Submersible GCS
Handles real-time streaming to CSV files and MicroSD sync.
"""
import os
import csv
import time
from datetime import datetime
from typing import Optional, Dict, Any


class DataLogger:
    """
    Manages CSV mission logging and file persistence.
    """

    CSV_HEADERS = [
        "TIMESTAMP_MS",
        "DATETIME_UTC",
        # Water Quality
        "TEMP_C",
        "PH",
        "DO_MGL",
        "COND_US_CM",
        # Raw Water Quality
        "RAW_TEMP_C",
        "RAW_PH",
        "RAW_DO_MGL",
        "RAW_COND_US_CM",
        # Power & Battery (Dual Battery)
        "BATT_V",
        "CURRENT_A",
        "SOC_PCT",
        "SOC_KALMAN_PCT",
        "SENSOR_BATT_V",
        "SENSOR_CURRENT_A",
        # Navigation & MARG
        "DEPTH_M",
        "RAW_PRESSURE_MBAR",
        "TARGET_DEPTH_M",
        "ERROR_DEPTH_M",
        "ROLL_DEG",
        "PITCH_DEG",
        "YAW_DEG",
        # 6 Thrusters PWM
        "PWM1_BOW_PORT",
        "PWM2_BOW_STBD",
        "PWM3_STERN_PORT",
        "PWM4_STERN_STBD",
        "PWM5_VERT_PORT",
        "PWM6_VERT_STBD",
        # LMPC & EKF State
        "LMPC_WCET_MS",
        "DISTURB_SURGE_N",
        "DISTURB_SWAY_N",
        "DISTURB_HEAVE_N",
        # EA-DSRA TBM (s)
        "TBM_TEMP_S",
        "TBM_PH_S",
        "TBM_DO_S",
        "TBM_COND_S",
        "WEA_PENALTY"
    ]

    def __init__(self, default_log_dir="./data_logs"):
        self.log_dir = default_log_dir
        self.is_recording = False
        self.current_file_path: Optional[str] = None
        self._file_handle = None
        self._csv_writer = None
        self.recorded_rows_count = 0
        self.start_time: Optional[datetime] = None
        self.interval: float = 0.0
        self._last_logged_time: float = 0.0

        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir, exist_ok=True)
            except Exception:
                pass

    def start_recording(self, mission_name: str = "mission", custom_dir: Optional[str] = None, interval: float = 0.0) -> str:
        """
        Starts a new CSV recording session with optional sampling interval throttle (seconds).
        interval=0.0 logs every received packet (~10 Hz).
        """
        save_dir = custom_dir if (custom_dir and os.path.isdir(custom_dir)) else self.log_dir
        os.makedirs(save_dir, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c for c in mission_name if c.isalnum() or c in ("-", "_")).strip()
        if not clean_name:
            clean_name = "submersible_log"

        filename = f"{clean_name}_{timestamp_str}.csv"
        self.current_file_path = os.path.join(save_dir, filename)

        self._file_handle = open(self.current_file_path, mode="w", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._file_handle)
        self._csv_writer.writerow(self.CSV_HEADERS)
        self._file_handle.flush()

        self.is_recording = True
        self.recorded_rows_count = 0
        self.start_time = datetime.now()
        self.interval = max(0.0, float(interval))
        self._last_logged_time = 0.0

        return self.current_file_path

    def log_telemetry(self, data: Dict[str, Any]):
        """
        Appends a telemetry record to the active CSV file, throttled by self.interval.
        """
        if not self.is_recording or not self._file_handle or not self._csv_writer:
            return

        now_ts = time.time()
        if self.interval > 0.0:
            if (now_ts - self._last_logged_time) < (self.interval - 0.005):
                return
        self._last_logged_time = now_ts

        now_str = datetime.now().isoformat()
        row = [
            data.get("timestamp", 0),
            now_str,
            # Water Quality
            f"{data.get('temp', 0.0):.2f}",
            f"{data.get('ph', 0.0):.2f}",
            f"{data.get('do', 0.0):.2f}",
            f"{data.get('cond', 0.0):.1f}",
            # Raw
            f"{data.get('raw_temp', 0.0):.2f}",
            f"{data.get('raw_ph', 0.0):.2f}",
            f"{data.get('raw_do', 0.0):.2f}",
            f"{data.get('raw_cond', 0.0):.1f}",
            # Power (Dual Battery)
            f"{data.get('battery_v', 0.0):.2f}",
            f"{data.get('current_a', 0.0):.2f}",
            f"{data.get('soc', 100.0):.1f}",
            f"{data.get('soc_kalman', 100.0):.1f}",
            f"{data.get('sensor_battery_v', 12.0):.2f}",
            f"{data.get('sensor_current_a', 0.0):.2f}",
            # Navigation
            f"{data.get('depth', 0.0):.2f}",
            f"{data.get('raw_pressure', 0.0):.2f}",
            f"{data.get('target_depth', 0.0):.2f}",
            f"{data.get('error_depth', 0.0):.2f}",
            f"{data.get('roll', 0.0):.1f}",
            f"{data.get('pitch', 0.0):.1f}",
            f"{data.get('yaw', 0.0):.1f}",
            # Thrusters
            data.get("pwm1", 1500),
            data.get("pwm2", 1500),
            data.get("pwm3", 1500),
            data.get("pwm4", 1500),
            data.get("pwm5", 1500),
            data.get("pwm6", 1500),
            # LMPC & Disturbance
            f"{data.get('lmpc_wcet_ms', 0.0):.2f}",
            f"{data.get('disturb_surge', 0.0):.2f}",
            f"{data.get('disturb_sway', 0.0):.2f}",
            f"{data.get('disturb_heave', 0.0):.2f}",
            # EA-DSRA
            f"{data.get('tbm_temp', 1.0):.2f}",
            f"{data.get('tbm_ph', 1.0):.2f}",
            f"{data.get('tbm_do', 1.0):.2f}",
            f"{data.get('tbm_cond', 1.0):.2f}",
            f"{data.get('wea_penalty', 1.0):.2f}"
        ]

        try:
            self._csv_writer.writerow(row)
            self.recorded_rows_count += 1
            if self.recorded_rows_count % 10 == 0:
                self._file_handle.flush()
        except Exception:
            pass

    def stop_recording(self) -> Dict[str, Any]:
        """
        Closes current CSV file and returns summary metrics.
        """
        if not self.is_recording:
            return {"file_path": None, "rows": 0, "duration_s": 0}

        self.is_recording = False
        duration_s = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0

        if self._file_handle:
            try:
                self._file_handle.flush()
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None
            self._csv_writer = None

        result = {
            "file_path": self.current_file_path,
            "rows": self.recorded_rows_count,
            "duration_s": duration_s
        }
        return result
