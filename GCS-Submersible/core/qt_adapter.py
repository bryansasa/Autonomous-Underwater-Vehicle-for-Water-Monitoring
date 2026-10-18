# -*- coding: utf-8 -*-
"""
Qt Service Adapter for Submersible Ground Control Station.
Acts as a thin, thread-safe bridge connecting pure Python GcsService
to PyQt5 main thread event loop via QtCore.pyqtSignal.
"""
from typing import Dict, Any, Optional
from PyQt5 import QtCore

from core.gcs_service import GcsService


class QtServiceAdapter(QtCore.QObject):
    """
    Translates pure Python GcsService events into PyQt5 signals for UI widgets.
    """
    # Core Telemetry & Status Signals
    telemetry_received = QtCore.pyqtSignal(object)
    connection_changed = QtCore.pyqtSignal(bool, str)
    log_emitted = QtCore.pyqtSignal(str)
    alert_triggered = QtCore.pyqtSignal(str, str, str)  # (level, title, desc)

    # Recording & Timer Signals
    recording_changed = QtCore.pyqtSignal(bool, str)     # (is_recording, filepath)
    recording_clock_tick = QtCore.pyqtSignal(str)        # "00:00:00"

    # Foxglove & Bridge Signals
    foxglove_changed = QtCore.pyqtSignal(bool, str)

    def __init__(self, config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.service = GcsService(config)

        # Connect pure Python EventHooks to Qt Signals safely
        self.service.telemetry_received.connect(lambda d: self.telemetry_received.emit(d))
        self.service.connection_changed.connect(lambda c, m: self.connection_changed.emit(c, m))
        self.service.log_emitted.connect(lambda m: self.log_emitted.emit(m))
        self.service.alert_triggered.connect(lambda l, t, d: self.alert_triggered.emit(l, t, d))
        self.service.recording_changed.connect(lambda r, f: self.recording_changed.emit(r, f))
        self.service.recording_clock_tick.connect(lambda t: self.recording_clock_tick.emit(t))
        self.service.foxglove_changed.connect(lambda r, m: self.foxglove_changed.emit(r, m))

    # =========================================================
    # --- DELEGATED CONTROL METHODS ---
    # =========================================================
    def start_connection(self, conn_type="TCP", ip="192.168.1.170", port=9000, serial_port="COM3", baud=115200):
        self.service.start_connection(conn_type=conn_type, ip=ip, port=port, serial_port=serial_port, baud=baud)

    def stop_connection(self):
        self.service.stop_connection()

    def set_operating_mode(self, mode: str):
        self.service.set_operating_mode(mode)

    def send_command(self, cmd: str):
        self.service.send_command(cmd)

    def arm(self, armed: bool):
        self.service.arm(armed)

    def emergency_kill(self):
        self.service.emergency_kill()

    def set_depth_setpoint(self, depth: float):
        self.service.set_depth_setpoint(depth)

    def start_recording(self, mission_name: str = "record_saguling", custom_dir: Optional[str] = None, interval: float = 0.0) -> str:
        return self.service.start_recording(mission_name=mission_name, custom_dir=custom_dir, interval=interval)

    def stop_recording(self) -> Dict[str, Any]:
        return self.service.stop_recording()

    def is_recording(self) -> bool:
        return self.service.is_recording()

    def toggle_foxglove(self, enable: bool):
        self.service.toggle_foxglove(enable)

    def is_connected(self) -> bool:
        return self.service.comm.is_connected()

    def update_config(self, new_config: Dict[str, Any]):
        self.service.update_config(new_config)

    def shutdown(self):
        self.service.shutdown()
