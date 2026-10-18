# -*- coding: utf-8 -*-
"""
CSV Data Logger for Calibration Sessions
Records timestamped multivariate sensor telemetries to CSV files with configurable intervals.
"""

import csv
from datetime import datetime
import os
from PyQt5 import QtCore


class DataLogger(QtCore.QObject):
    status_updated = QtCore.pyqtSignal(str, str)  # status_text, style_class
    sample_recorded = QtCore.pyqtSignal(int, str)  # total_count, time_str

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.csv_file = None
        self.csv_writer = None
        self.record_count = 0
        self.record_start_time = None
        self.last_write_time = None
        self.interval = 1.0
        self.save_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
        self.current_filepath = ""

        # Ensure default logs dir exists
        os.makedirs(self.save_directory, exist_ok=True)

    def start_recording(self, save_dir: str = None, interval: float = 1.0) -> bool:
        if self.is_recording:
            return True

        if save_dir:
            self.save_directory = save_dir
        os.makedirs(self.save_directory, exist_ok=True)

        self.interval = max(0.1, interval)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"calib_session_{ts_str}.csv"
        self.current_filepath = os.path.join(self.save_directory, filename)

        try:
            self.csv_file = open(self.current_filepath, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)
            # Comprehensive header matching both Water Quality and Motion IMU
            self.csv_writer.writerow([
                "Datetime", "Teensy_ms",
                "pH", "Conductivity_uS", "DO_mgL", "Temperature_C",
                "Roll_deg", "Pitch_deg", "Yaw_deg", "Depth_m", "Pressure_mbar"
            ])
            self.csv_file.flush()

            self.is_recording = True
            self.record_count = 0
            self.record_start_time = datetime.now()
            self.last_write_time = None

            self.status_updated.emit(f"Merekam... ({filename})", "recording")
            return True
        except Exception as e:
            self.is_recording = False
            self.status_updated.emit(f"Gagal membuat file CSV: {e}", "error")
            return False

    def log_telemetry(self, data: dict):
        if not self.is_recording or not self.csv_writer:
            return

        now = datetime.now()
        if self.last_write_time is not None:
            elapsed_since_last = (now - self.last_write_time).total_seconds()
            if elapsed_since_last < self.interval:
                return

        now_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        row = [
            now_str,
            data.get("ts", 0),
            f"{data.get('ph', 0.0):.3f}",
            f"{data.get('ec', 0.0):.1f}",
            f"{data.get('do', 0.0):.3f}",
            f"{data.get('temp', 0.0):.2f}",
            f"{data.get('roll', 0.0):.2f}",
            f"{data.get('pitch', 0.0):.2f}",
            f"{data.get('yaw', 0.0):.2f}",
            f"{data.get('depth', 0.0):.3f}",
            f"{data.get('press', 1013.25):.2f}"
        ]

        try:
            self.csv_writer.writerow(row)
            self.csv_file.flush()
            self.record_count += 1
            self.last_write_time = now

            # Duration string
            total_sec = int((now - self.record_start_time).total_seconds())
            hours, rem = divmod(total_sec, 3600)
            mins, secs = divmod(rem, 60)
            time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"

            self.sample_recorded.emit(self.record_count, time_str)
        except Exception:
            pass

    def stop_recording(self) -> str:
        if not self.is_recording:
            return ""

        self.is_recording = False
        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
            self.csv_writer = None

        saved_path = self.current_filepath
        self.status_updated.emit(f"Tersimpan {self.record_count} sampel ({os.path.basename(saved_path)})", "idle")
        return saved_path
