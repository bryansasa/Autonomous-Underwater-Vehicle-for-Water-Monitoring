# -*- coding: utf-8 -*-
"""
Live Camera Feed Widget for Tyrant-AQ AUV GCS
Supports:
  - USB Underwater Webcams / Frame Grabbers (Device 0, 1, 2)
  - RTSP / HTTP IP Camera Streams
  - Simulated Underwater Video Feed (Caustics, bubbles & telemetry HUD overlay)
  - 1-Click Full-Resolution Snapshot Capture (saved to data_logs/snapshots/)
"""
from __future__ import annotations
import os
import time
import math
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List

from PyQt5 import QtWidgets, QtCore, QtGui


class CameraWorker(QtCore.QThread):
    """
    Dedicated background thread capturing frames to prevent any UI stutter.
    """
    frame_captured = QtCore.pyqtSignal(QtGui.QImage)
    status_changed = QtCore.pyqtSignal(str)

    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self.running = False
        self._lock = QtCore.QMutex()
        self.current_cv_frame = None

        # Telemetry overlay data
        self.telemetry = {
            "depth": 0.0,
            "yaw": 0.0,
            "temp": 27.0,
            "batt_v": 24.5
        }

    def set_source(self, source):
        self.source = source

    def update_telemetry(self, data: Dict[str, Any]):
        self.telemetry["depth"] = data.get("depth", 0.0)
        self.telemetry["yaw"] = data.get("yaw", 0.0)
        self.telemetry["temp"] = data.get("temp", 27.0)
        self.telemetry["batt_v"] = data.get("battery_v", 24.5)

    def run(self):
        self.running = True

        # Check if source is simulated feed
        if str(self.source).upper() == "SIMULATION":
            self.run_simulation_feed()
            return

        # Attempt to open OpenCV VideoCapture
        cap = None
        try:
            src = int(self.source) if str(self.source).isdigit() else str(self.source)
            cap = cv2.VideoCapture(src)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if not cap.isOpened():
                self.status_changed.emit(f"Kamera '{self.source}' tidak dapat dibuka. Mengalihkan ke Simulasi Feed...")
                time.sleep(1.0)
                self.run_simulation_feed()
                return

            self.status_changed.emit(f"Kamera aktif: {self.source}")

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                self.current_cv_frame = frame.copy()
                self._emit_frame(frame)
                time.sleep(0.033)  # ~30 FPS

        except Exception as e:
            self.status_changed.emit(f"Camera Error: {e}")
            self.run_simulation_feed()
        finally:
            if cap and cap.isOpened():
                cap.release()

    def run_simulation_feed(self):
        """Generates synthetic underwater video feed with animated caustics & HUD."""
        self.status_changed.emit("Kamera Feed: Simulasi Bawah Air (Synthetic)")
        step = 0
        w, h = 640, 480

        while self.running:
            step += 1
            t = step * 0.05

            # 1. Base underwater deep cyan gradient
            grad = np.tile(np.linspace(15, 60, h, dtype=np.uint8)[:, None], (1, w))
            b_channel = np.clip(grad + 120 + 20 * np.sin(t), 0, 255).astype(np.uint8)
            g_channel = np.clip(grad * 0.7 + 60 + 15 * np.cos(t * 0.8), 0, 255).astype(np.uint8)
            r_channel = np.clip(grad * 0.2 + 10, 0, 255).astype(np.uint8)
            frame = cv2.merge([b_channel, g_channel, r_channel])

            # 2. Simulated water caustic rays & floating particles
            for i in range(5):
                cx = int((w / 2) + 150 * math.sin(t * 0.7 + i * 1.2))
                cy = int((h / 2) + 100 * math.cos(t * 0.5 + i * 0.9))
                cv2.circle(frame, (cx, cy), 18 + i * 4, (200, 240, 255), -1)

            # Gaussian blur for soft underwater light effect
            frame = cv2.GaussianBlur(frame, (25, 25), 0)

            # Simulated sonar / crosshair grid
            cv2.circle(frame, (w // 2, h // 2), 60, (0, 210, 255), 1)
            cv2.line(frame, (w // 2 - 80, h // 2), (w // 2 + 80, h // 2), (0, 210, 255), 1)
            cv2.line(frame, (w // 2, h // 2 - 80), (w // 2, h // 2 + 80), (0, 210, 255), 1)

            self.current_cv_frame = frame.copy()
            self._emit_frame(frame)
            time.sleep(0.04)  # ~25 FPS

    def _emit_frame(self, cv_bgr_frame):
        # Draw HUD overlay directly onto frame
        h, w, _ = cv_bgr_frame.shape
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cv2.putText(cv_bgr_frame, f"TYRANT-AQ CAM 1 | {ts_str}", (15, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.putText(cv_bgr_frame, f"DEPTH: {self.telemetry['depth']:.2f} m | HDG: {self.telemetry['yaw']:.1f} deg",
                    (15, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 200), 1)
        cv2.putText(cv_bgr_frame, f"BATT: {self.telemetry['batt_v']:.1f} V | TEMP: {self.telemetry['temp']:.1f} C",
                    (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 200), 1)

        # Convert OpenCV BGR to Qt QImage
        rgb_frame = cv2.cvtColor(cv_bgr_frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        q_img = QtGui.QImage(rgb_frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888).copy()
        self.frame_captured.emit(q_img)

    def stop(self):
        self.running = False
        self.wait(500)


class CameraFeedWidget(QtWidgets.QWidget):
    """
    User Interface Widget for Camera Live Video Feed & Snapshot.
    Supports seamless sharing of the camera stream between full and split views.
    """
    snapshot_saved = QtCore.pyqtSignal(str)

    _shared_worker: Optional[CameraWorker] = None
    _active_instances: List['CameraFeedWidget'] = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 110)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.current_qimg: Optional[QtGui.QImage] = None
        self.snapshot_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data_logs", "snapshots")
        os.makedirs(self.snapshot_dir, exist_ok=True)

        CameraFeedWidget._active_instances.append(self)
        self.init_ui()

        # If shared camera is already running, connect this instance immediately!
        if CameraFeedWidget._shared_worker and CameraFeedWidget._shared_worker.isRunning():
            CameraFeedWidget._shared_worker.frame_captured.connect(self.on_frame_captured)
            self._update_ui_state(is_running=True)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # 1. Video Display Label Frame
        self.video_frame = QtWidgets.QLabel("Kamera Belum Aktif\nKlik 'Start Cam' untuk memulai streaming.")
        self.video_frame.setAlignment(QtCore.Qt.AlignCenter)
        self.video_frame.setStyleSheet("""
            background-color: #1A1D23;
            border: 1px solid #363C46;
            border-radius: 6px;
            color: #9AA0A6;
            font-size: 11px;
            font-weight: bold;
        """)
        self.video_frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.video_frame.setCursor(QtCore.Qt.PointingHandCursor)
        self.video_frame.mousePressEvent = lambda e: self.toggle_camera()
        layout.addWidget(self.video_frame, stretch=1)

        # 2. Control Bar (Source Selector, Start/Stop, Snapshot)
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setContentsMargins(2, 0, 2, 0)
        ctrl_bar.setSpacing(4)

        ctrl_bar.addWidget(QtWidgets.QLabel("Sumber:"))
        self.combo_source = QtWidgets.QComboBox()
        self.combo_source.addItems(["Cam 0 (USB)", "Cam 1 (USB)", "Cam 2 (USB)", "SIMULATION", "RTSP Stream URL"])
        self.combo_source.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.combo_source.setStyleSheet("padding: 2px 4px; font-size: 10px;")
        ctrl_bar.addWidget(self.combo_source)

        self.btn_toggle_cam = QtWidgets.QPushButton("Start Cam")
        self.btn_toggle_cam.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 10px;")
        self.btn_toggle_cam.clicked.connect(self.toggle_camera)
        ctrl_bar.addWidget(self.btn_toggle_cam)

        self.btn_snapshot = QtWidgets.QPushButton("Snapshot")
        self.btn_snapshot.setStyleSheet("background-color: #333333; border: 1px solid #444444; color: white; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 10px;")
        self.btn_snapshot.clicked.connect(self.take_snapshot)
        ctrl_bar.addWidget(self.btn_snapshot)

        layout.addLayout(ctrl_bar)

    def toggle_camera(self):
        if CameraFeedWidget._shared_worker and CameraFeedWidget._shared_worker.isRunning():
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        src_text = self.combo_source.currentText()
        if "SIMULATION" in src_text:
            source = "SIMULATION"
        elif "Cam 0" in src_text:
            source = 0
        elif "Cam 1" in src_text:
            source = 1
        elif "Cam 2" in src_text:
            source = 2
        else:
            url, ok = QtWidgets.QInputDialog.getText(self, "RTSP IP Camera", "Masukkan URL RTSP / HTTP Stream:",
                                                    QtWidgets.QLineEdit.Normal, "rtsp://192.168.1.180:554/live")
            if not ok or not url:
                return
            source = url.strip()

        # Stop existing worker if running
        if CameraFeedWidget._shared_worker:
            try:
                CameraFeedWidget._shared_worker.stop()
            except Exception:
                pass

        worker = CameraWorker(source=source)
        CameraFeedWidget._shared_worker = worker

        # Connect all active CameraFeedWidget instances
        for inst in CameraFeedWidget._active_instances:
            worker.frame_captured.connect(inst.on_frame_captured)
            inst._update_ui_state(is_running=True, source_text=src_text)

        worker.start()

    def stop_camera(self):
        if CameraFeedWidget._shared_worker:
            try:
                CameraFeedWidget._shared_worker.stop()
            except Exception:
                pass
            CameraFeedWidget._shared_worker = None

        for inst in CameraFeedWidget._active_instances:
            inst._update_ui_state(is_running=False)

    def _update_ui_state(self, is_running: bool, source_text: Optional[str] = None):
        if source_text and self.combo_source.findText(source_text) != -1:
            self.combo_source.blockSignals(True)
            self.combo_source.setCurrentText(source_text)
            self.combo_source.blockSignals(False)

        if is_running:
            self.btn_toggle_cam.setText("Stop Cam")
            self.btn_toggle_cam.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 10px;")
        else:
            self.video_frame.setText("Kamera Belum Aktif\nKlik 'Start Cam' untuk memulai streaming.")
            self.btn_toggle_cam.setText("Start Cam")
            self.btn_toggle_cam.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 10px;")

    def on_frame_captured(self, q_img: QtGui.QImage):
        self.current_qimg = q_img
        target_size = self.video_frame.size()
        if target_size.width() > 10 and target_size.height() > 10:
            scaled_pixmap = QtGui.QPixmap.fromImage(q_img).scaled(
                target_size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.video_frame.setPixmap(scaled_pixmap)

    def update_telemetry(self, data: Dict[str, Any]):
        if CameraFeedWidget._shared_worker:
            CameraFeedWidget._shared_worker.update_telemetry(data)

    def take_snapshot(self):
        worker = CameraFeedWidget._shared_worker
        if worker and worker.current_cv_frame is not None:
            ts_file = datetime.now().strftime("snap_%Y%m%d_%H%M%S.jpg")
            path = os.path.join(self.snapshot_dir, ts_file)
            cv2.imwrite(path, worker.current_cv_frame)
            self.snapshot_saved.emit(path)
            QtWidgets.QMessageBox.information(
                self, "Snapshot Berhasil",
                f"Foto tersimpan di:\n{path}"
            )
        else:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Kamera belum aktif untuk mengambil snapshot.")

    def closeEvent(self, event):
        if self in CameraFeedWidget._active_instances:
            CameraFeedWidget._active_instances.remove(self)
        super().closeEvent(event)
