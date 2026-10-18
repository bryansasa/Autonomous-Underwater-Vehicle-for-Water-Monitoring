# -*- coding: utf-8 -*-
"""
Unified Core Service for Submersible Ground Control Station.
Orchestrates:
  - Communication Engine (TCP/UDP/Serial/Simulator)
  - CSV Data Logger
  - Safety Alert Engine
  - Foxglove Studio WebSocket Bridge
Pure Python architecture completely decoupled from GUI & widgets.
"""
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from core.comm_engine import CommEngine
from core.data_logger import DataLogger
from core.alert_engine import AlertEngine
from core.foxglove_bridge import FoxgloveBridgeServer
from core.event_hook import EventHook


class GcsService:
    """
    Central backend service managing vehicle communications, logging, alerts, and bridges.
    100% headless, testable without UI, and reusable in ROS2 or CLI environments.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # 1. Initialize Core Engines
        self.comm = CommEngine()
        self.logger = DataLogger(self.config.get("record_path", "./data_logs"))
        self.alert_engine = AlertEngine(self.config)
        self.foxglove = FoxgloveBridgeServer(
            host=self.config.get("foxglove_host", "0.0.0.0"),
            port=self.config.get("foxglove_port", 8765)
        )

        # 2. Recording Clock & State
        self.rec_start_time: Optional[datetime] = None
        self._clock_running = True
        self._clock_thread = threading.Thread(target=self._clock_loop, daemon=True, name="GcsServiceClock")

        # 3. High-level Event Hooks for Listeners (UI / CLI / ROS2)
        self.telemetry_received = EventHook()      # (data: dict)
        self.connection_changed = EventHook()      # (is_connected: bool, message: str)
        self.log_emitted = EventHook()            # (message: str)
        self.alert_triggered = EventHook()         # (level: str, key: str, description: str)
        self.recording_changed = EventHook()       # (is_recording: bool, filepath_or_info: str)
        self.recording_clock_tick = EventHook()    # (formatted_time: str)
        self.foxglove_changed = EventHook()        # (is_running: bool, message: str)

        # 4. Wire internal pipelines
        self._wire_pipelines()
        self._clock_thread.start()

    def _wire_pipelines(self):
        # Comm -> Pipeline
        self.comm.telemetry_received.connect(self._on_telemetry_packet)
        self.comm.connection_changed.connect(self.connection_changed.emit)
        self.comm.log_emitted.connect(self.log_emitted.emit)

        # Alert -> Pipeline
        self.alert_engine.alert_triggered.connect(self.alert_triggered.emit)

        # Foxglove -> Pipeline
        self.foxglove.server_status_changed.connect(self.foxglove_changed.emit)
        self.foxglove.log_emitted.connect(self.log_emitted.emit)

    def _on_telemetry_packet(self, data: Dict[str, Any]):
        # 1. Stream to CSV logger if recording
        if self.logger.is_recording:
            self.logger.log_telemetry(data)

        # 2. Evaluate Safety Thresholds
        self.alert_engine.evaluate_telemetry(data)

        # 3. Stream to Foxglove Studio WebSocket if active
        if self.foxglove.is_running:
            self.foxglove.broadcast_telemetry(data)

        # 4. Dispatch to external subscribers (UI, CLI, ROS2)
        self.telemetry_received.emit(data)

    def _clock_loop(self):
        while self._clock_running:
            if self.logger.is_recording and self.rec_start_time:
                elapsed = datetime.now() - self.rec_start_time
                total_sec = int(elapsed.total_seconds())
                h, rem = divmod(total_sec, 3600)
                m, s = divmod(rem, 60)
                clock_str = f"{h:02}:{m:02}:{s:02}"
            else:
                clock_str = "00:00:00"
            self.recording_clock_tick.emit(clock_str)
            time.sleep(0.5)

    # =========================================================
    # --- PUBLIC CONTROL API ---
    # =========================================================
    def start_connection(self, conn_type="TCP", ip="192.168.1.170", port=9000, serial_port="COM3", baud=115200):
        self.comm.start(conn_type=conn_type, ip=ip, port=port, serial_port=serial_port, baud=baud)

    def stop_connection(self):
        self.comm.stop()

    def set_operating_mode(self, mode: str):
        self.comm.set_operating_mode(mode)

    def send_command(self, cmd: str):
        self.comm.send_command(cmd)

    def arm(self, armed: bool):
        cmd = "ARM\n" if armed else "DISARM\n"
        self.send_command(cmd)

    def emergency_kill(self):
        self.send_command("KILL\n")
        self.send_command("STOP_ALL\n")
        self.log_emitted.emit("[EMERGENCY] Sinyal EMERGENCY KILL & STOP ALL dikirim!")

    def set_depth_setpoint(self, depth: float):
        self.send_command(f"SETPOINT,{depth:.2f}\n")

    def start_recording(self, mission_name: str = "record_saguling", custom_dir: Optional[str] = None, interval: float = 0.0) -> str:
        filepath = self.logger.start_recording(mission_name=mission_name, custom_dir=custom_dir, interval=interval)
        self.rec_start_time = datetime.now()
        self.recording_changed.emit(True, filepath)
        interval_desc = f"interval {interval:.2f}s" if interval > 0.0 else "semua data (~10 Hz)"
        self.log_emitted.emit(f"[RECORD] Perekaman CSV dimulai: {filepath} ({interval_desc})")
        return filepath

    def stop_recording(self) -> Dict[str, Any]:
        res = self.logger.stop_recording()
        self.rec_start_time = None
        self.recording_changed.emit(False, res["file_path"])
        self.log_emitted.emit(f"[RECORD] Perekaman selesai ({res['rows']} baris dalam {res['duration_s']:.1f}s).")
        return res

    def is_recording(self) -> bool:
        return self.logger.is_recording

    def toggle_foxglove(self, enable: bool):
        if enable:
            self.foxglove.start_server()
        else:
            self.foxglove.stop_server()

    def update_config(self, new_config: Dict[str, Any]):
        """Update active configuration parameters dynamically across all engines."""
        self.config = new_config
        if hasattr(self, "alert_engine"):
            self.alert_engine.config = new_config
        if hasattr(self, "logger") and "record_path" in new_config:
            self.logger.base_dir = new_config.get("record_path", "./data_logs")

    def shutdown(self):
        self._clock_running = False
        self.comm.stop()
        if self.logger.is_recording:
            self.logger.stop_recording()
        self.foxglove.stop_server()
