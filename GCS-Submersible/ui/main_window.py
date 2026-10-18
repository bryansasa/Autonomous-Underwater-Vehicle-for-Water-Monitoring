# -*- coding: utf-8 -*-
"""
Main Window for Tyrant-AQ AUV Ground Control Station (GCS)
Organized in 3 Clean Tabs:
  Tab 1: Kontrol Wahana, Monitor Sensor & Rekam Data (Includes 3D Orientation & Camera Feed)
  Tab 2: Visualisasi Grafik Sensor (4 Slot Interaktif)
  Tab 3: Import & Analisis Berkas CSV (Offline Viewer)
Includes:
  - Real Hardware vs Built-in Dummy Simulator Switcher
  - Foxglove Studio WebSocket Bridge (:8765)
  - 3D Submersible Navigation & Tactical PFD HUD
  - Deadman Switch Keyboard W/S Control
  - QGC Dark / Light theme support.
"""
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any

from PyQt5 import QtWidgets, QtCore, QtGui

from core.qt_adapter import QtServiceAdapter
from core.joystick_manager import JoystickManager

from ui.widgets.quick_action_bar import QuickActionBar
from ui.widgets.main_control_tab import MainControlTab
from ui.widgets.sensor_graph_tab import SensorGraphTab
from ui.widgets.csv_importer_tab import CSVImporterTab
from ui.widgets.mission_control import MissionControl
from ui.widgets.config_settings_tab import ConfigSettingsTab


class MainWindow(QtWidgets.QMainWindow):
    """
    Main Ground Control Station Application Window.
    """

    def __init__(self, config_path: str = "./config/gui_config.json"):
        super().__init__()
        self.config_path = config_path
        self.config = self.load_config()

        self.setWindowTitle("Tyrant-AQ AUV | Ground Control Station (GCS)")
        self.resize(1380, 860)
        self.setMinimumSize(1024, 680)

        # Core Backend Service Adapter (Decoupled pure-Python communication & telemetry engine)
        self.adapter = QtServiceAdapter(self.config)

        # Joystick Setup
        self.joystick_mgr = JoystickManager(
            deadzone=self.config.get("joystick_deadzone", 0.15),
            max_speed=self.config.get("joystick_max_speed", 250)
        )

        # Build UI
        self.init_ui()
        self.connect_signals()

        # Apply Theme
        self.apply_theme(self.config.get("theme", "Dark Mode"))

        # Joystick Setup
        if self.config.get("joystick_enabled", True):
            self.joystick_mgr.initialize()

        # Start default in SIMULATION mode for immediate dummy testing
        self.adapter.set_operating_mode("SIMULATION")

        self.tab_control.append_log("=== Sistem Ground Control Station Submersible Aktif ===")
        self.tab_control.append_log("[INFO] Mode Default: SIMULASI DUMMY (Siap Uji Langsung)")

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {}

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.tab_control.append_log(f"[CONFIG ERROR] Gagal menyimpan config: {e}")

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QtWidgets.QVBoxLayout(central_widget)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # 1. Top Quick Action Bar
        self.action_bar = QuickActionBar()
        root_layout.addWidget(self.action_bar)

        # 2. Main Tab Widget (Organized Navigation Tabs)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.tabBar().setElideMode(QtCore.Qt.ElideNone)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                font-size: 11px;
                font-weight: bold;
                padding: 6px 16px;
                min-height: 24px;
            }
        """)

        # Tab 1: 01 Operasi (3D Navigasi, Kamera HUD, Kualitas Air & Daya)
        self.tab_control = MainControlTab()
        self.tabs.addTab(self.tab_control, "01 Operasi")

        # Tab 2: 02 Kontrol & Misi (Kendali Manual, Referensi Target & Tactical Mission Planner)
        self.tab_mission = MissionControl()
        self.tabs.addTab(self.tab_mission, "02 Kontrol && Misi")

        # Tab 3: 03 Grafik & Rekaman (Visualisasi Multi-Slot Grafik Sensor Realtime)
        self.tab_graphs = SensorGraphTab()
        self.tabs.addTab(self.tab_graphs, "03 Grafik && Rekaman")

        # Tab 4: 04 Diagnostik & Tuning (Diagnostik Sistem, Parameter LMPC/EA-DSRA & JSON Config)
        self.tab_settings = ConfigSettingsTab(config_path=self.config_path, current_config=self.config)
        self.tabs.addTab(self.tab_settings, "04 Diagnostik && Tuning")

        # Tab 5: Analisis CSV (Inspeksi & Plotting Data Rekaman Offline)
        self.tab_csv = CSVImporterTab()
        self.tabs.addTab(self.tab_csv, "05 Analisis CSV")

        root_layout.addWidget(self.tabs, stretch=1)

        # Give keyboard focus to window for Deadman W/S
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def connect_signals(self):
        # Backend Core Adapter Signals
        self.adapter.telemetry_received.connect(self.on_telemetry_received)
        self.adapter.connection_changed.connect(self.on_connection_changed)
        self.adapter.log_emitted.connect(self.tab_control.append_log)
        self.adapter.alert_triggered.connect(self.on_safety_alert)
        self.adapter.recording_clock_tick.connect(self.tab_control.set_recording_timer_text)

        # Quick Action Bar
        self.action_bar.connect_requested.connect(self.toggle_network_connection)
        self.action_bar.operating_mode_changed.connect(self.adapter.set_operating_mode)
        self.action_bar.foxglove_toggle_requested.connect(self.adapter.toggle_foxglove)
        self.action_bar.mode_changed.connect(lambda m: self.adapter.send_command(f"MODE,{m}\n"))
        self.action_bar.arm_state_changed.connect(self.adapter.arm)
        self.action_bar.emergency_kill_triggered.connect(self.on_emergency_kill)

        # Camera Snapshot Notifications
        self.tab_control.widget_cam.snapshot_saved.connect(
            lambda path: self.tab_control.append_log(f"[CAMERA SNAPSHOT] Disimpan di: {path}")
        )
        self.tab_control.split_cam.snapshot_saved.connect(
            lambda path: self.tab_control.append_log(f"[CAMERA SNAPSHOT] Disimpan di: {path}")
        )

        # Tab 1 Signals
        self.tab_control.command_generated.connect(self.adapter.send_command)
        self.tab_control.start_recording_requested.connect(self.start_csv_recording)
        self.tab_control.stop_recording_requested.connect(self.stop_csv_recording)
        self.tab_control.sd_download_requested.connect(lambda fn: self.adapter.send_command(f"SD_DOWNLOAD,{fn}\n"))
        self.tab_control.theme_changed_signal.connect(self.apply_theme)
        self.tab_control.connect_ethernet_requested.connect(self.connect_ethernet_target)
        self.tab_control.connect_usb_requested.connect(self.connect_usb_port)

        # Tab 2: Mission Control Signals
        self.tab_mission.command_generated.connect(self.adapter.send_command)
        self.tab_mission.command_generated.connect(
            lambda cmd: self.tab_control.append_log(f">>> [MISI/TARGET] {cmd.strip()}")
        )
        self.tab_mission.manual_scale_changed.connect(
            lambda scale: self.tab_control.slider_speed.setValue(int(50 + scale * 350))
        )

        # Tab 6: Konfigurasi & Manajemen Parameter JSON Signals
        self.tab_settings.config_applied.connect(self.on_config_applied)
        self.tab_settings.command_generated.connect(self.adapter.send_command)
        self.tab_settings.theme_changed.connect(self.apply_theme)
        self.tab_settings.log_emitted.connect(self.tab_control.append_log)

        # Joystick Motion Inputs
        self.joystick_mgr.motion_command_emitted.connect(self.on_joystick_motion)

    def _find_theme_stylesheet(self, theme_name: str) -> str:
        style_file = "qgc_dark.qss" if "Dark" in theme_name else "qgc_light.qss"
        candidates = [
            os.path.join(os.path.dirname(__file__), "styles", style_file),
            os.path.join(os.path.dirname(__file__), "..", "ui", "styles", style_file),
        ]
        if hasattr(sys, "_MEIPASS"):
            candidates.insert(0, os.path.join(sys._MEIPASS, "ui", "styles", style_file))
            candidates.insert(1, os.path.join(sys._MEIPASS, "styles", style_file))
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "ui", "styles", style_file))
            candidates.append(os.path.join(exe_dir, "styles", style_file))

        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    print(f"Error reading stylesheet {p}: {e}")

        # Embedded Fallback Stylesheet so UI never falls back to unstyled white/broken look
        if "Dark" in theme_name:
            return """
                QMainWindow, QDialog, QWidget { background-color: #181818; color: #E0E0E0; font-family: 'Segoe UI', 'Roboto', sans-serif; font-size: 11px; }
                QGroupBox { background-color: #161922; border: 1px solid #252b3b; border-radius: 6px; margin-top: 14px; font-weight: 700; color: #cbd5e1; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; left: 8px; color: #f1f5f9; }
                QFrame#hudCard { background-color: #131620; border: 1px solid #222838; border-radius: 6px; }
                QTabWidget::pane { border: 1px solid #333333; background-color: #222222; border-radius: 4px; }
                QTabBar::tab { background-color: #242424; color: #9E9E9E; padding: 7px 16px; margin-right: 2px; border: 1px solid #333333; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; font-weight: 600; }
                QTabBar::tab:selected { background-color: #181818; color: #FFFFFF; border-top: 2px solid #E53935; border-bottom: 2px solid #181818; font-weight: 700; }
                QPushButton { background-color: #333333; border: 1px solid #444444; color: #E0E0E0; padding: 6px 14px; border-radius: 4px; font-weight: 600; }
                QPushButton:hover { background-color: #444444; border-color: #666666; color: #FFFFFF; }
                QPushButton#btnPrimary, QPushButton#btnStart { background-color: #D32F2F; border-color: #B71C1C; color: #FFFFFF; font-weight: 700; }
                QPushButton#btnDanger, QPushButton#btnStop, QPushButton#btnKill { background-color: #C62828; border-color: #8E0000; color: #FFFFFF; font-weight: 700; }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #1A1A1A; border: 1px solid #383838; color: #E0E0E0; padding: 5px 8px; border-radius: 4px; }
                QPlainTextEdit, QTextBrowser { background-color: #141414; border: 1px solid #333333; color: #C8C8C8; font-family: monospace; }
                QProgressBar { border: 1px solid #383838; border-radius: 3px; background-color: #1A1A1A; text-align: center; color: #FFFFFF; }
                QProgressBar::chunk { background-color: #D32F2F; border-radius: 2px; }
            """
        else:
            return """
                QMainWindow, QDialog, QWidget { background-color: #F0F2F5; color: #1F2937; font-family: 'Segoe UI', 'Roboto', sans-serif; font-size: 11px; }
                QFrame, QGroupBox { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 6px; }
                QGroupBox { margin-top: 16px; font-weight: 600; font-size: 12px; color: #2563EB; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; left: 10px; }
                QFrame#hudCard { background-color: #F9FAFB; border: 1px solid #D1D5DB; border-radius: 6px; }
                QTabWidget::pane { border: 1px solid #D1D5DB; background-color: #FFFFFF; border-radius: 6px; }
                QTabBar::tab { background-color: #E5E7EB; color: #6B7280; padding: 8px 16px; margin-right: 3px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: 600; }
                QTabBar::tab:selected { background-color: #FFFFFF; color: #2563EB; border-bottom: 2px solid #2563EB; }
                QPushButton { background-color: #F0F2F5; border: 1px solid #D1D5DB; color: #1F2937; padding: 7px 14px; border-radius: 6px; font-weight: 600; }
                QPushButton:hover { background-color: #E5E7EB; border-color: #6B7280; }
                QPushButton#btnPrimary, QPushButton#btnStart { background-color: #16A34A; border-color: #15803D; color: #FFFFFF; }
                QPushButton#btnDanger, QPushButton#btnStop, QPushButton#btnKill { background-color: #DC2626; border-color: #B91C1C; color: #FFFFFF; }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #FFFFFF; border: 1px solid #D1D5DB; color: #1F2937; padding: 6px 10px; border-radius: 6px; }
                QPlainTextEdit, QTextBrowser { background-color: #F9FAFB; border: 1px solid #D1D5DB; color: #374151; font-family: monospace; }
                QProgressBar { border: 1px solid #D1D5DB; border-radius: 4px; background-color: #E5E7EB; text-align: center; color: #1F2937; }
                QProgressBar::chunk { background-color: #16A34A; border-radius: 3px; }
            """

    def apply_theme(self, theme_name: str):
        qss_content = self._find_theme_stylesheet(theme_name)
        if qss_content:
            app_inst = QtWidgets.QApplication.instance()
            if app_inst:
                app_inst.setStyleSheet(qss_content)
            self.setStyleSheet(qss_content)

        # Propagate theme to sub-widgets
        if hasattr(self, "action_bar") and hasattr(self.action_bar, "apply_theme"):
            self.action_bar.apply_theme(theme_name)
        if hasattr(self, "tab_control") and hasattr(self.tab_control, "apply_theme"):
            self.tab_control.apply_theme(theme_name)
        if hasattr(self, "tab_graphs") and hasattr(self.tab_graphs, "apply_theme"):
            self.tab_graphs.apply_theme(theme_name)
        if hasattr(self, "tab_csv") and hasattr(self.tab_csv, "apply_theme"):
            self.tab_csv.apply_theme(theme_name)
        if hasattr(self, "tab_water_power") and hasattr(self.tab_water_power, "apply_theme"):
            self.tab_water_power.apply_theme(theme_name)

        # Synchronize Theme ComboBoxes
        if hasattr(self, "tab_control") and hasattr(self.tab_control, "combo_theme"):
            self.tab_control.combo_theme.blockSignals(True)
            self.tab_control.combo_theme.setCurrentText(theme_name)
            self.tab_control.combo_theme.blockSignals(False)

        if hasattr(self, "tab_settings") and hasattr(self.tab_settings, "cb_theme"):
            self.tab_settings.cb_theme.blockSignals(True)
            self.tab_settings.cb_theme.setCurrentText(theme_name)
            self.tab_settings.cb_theme.blockSignals(False)

        self.config["theme"] = theme_name
        self.save_config()

    def on_config_applied(self, new_config: Dict[str, Any]):
        """Handler when user saves, applies, or loads new configuration profiles."""
        self.config = new_config
        self.save_config()
        self.adapter.update_config(new_config)

        # Update joystick manager live
        if hasattr(self, "joystick_mgr"):
            self.joystick_mgr.deadzone = float(new_config.get("joystick_deadzone", 0.15))
            self.joystick_mgr.max_speed = int(new_config.get("joystick_max_speed", 250))

        # Synchronize LMPC widgets in Tab 1 & Tab 3
        lmpc = new_config.get("lmpc_defaults", {})
        if hasattr(self.tab_control, "txt_np"):
            self.tab_control.txt_np.setText(str(lmpc.get("np", 10)))
        if hasattr(self.tab_control, "txt_nc"):
            self.tab_control.txt_nc.setText(str(lmpc.get("nc", 3)))

        if hasattr(self.tab_mission, "sp_np"):
            self.tab_mission.sp_np.setValue(int(lmpc.get("np", 10)))
        if hasattr(self.tab_mission, "sp_nc"):
            self.tab_mission.sp_nc.setValue(int(lmpc.get("nc", 3)))
        if hasattr(self.tab_mission, "sp_qz"):
            self.tab_mission.sp_qz.setValue(float(lmpc.get("q_z", 100.0)))
        if hasattr(self.tab_mission, "sp_r"):
            self.tab_mission.sp_r.setValue(float(lmpc.get("r_thrust", 0.1)))

        # Synchronize EA-DSRA widgets in Tab 1 & Tab 2
        ea_cfg = new_config.get("ea_dsra_defaults", {})
        soc_th = float(ea_cfg.get("soc_threshold", 30.0))
        if hasattr(self.tab_control, "sp_tab1_soc_th"):
            self.tab_control.sp_tab1_soc_th.setValue(soc_th)
        if hasattr(self.tab_mission, "sp_soc_th"):
            self.tab_mission.sp_soc_th.setValue(soc_th)
        if hasattr(self.tab_mission, "sp_ph_e"):
            self.tab_mission.sp_ph_e.setValue(float(ea_cfg.get("ph", {}).get("e", 0.05)))
        if hasattr(self.tab_mission, "sp_ph_s"):
            self.tab_mission.sp_ph_s.setValue(int(ea_cfg.get("ph", {}).get("s", 300)))

        # Synchronize Recording path
        rec_path = new_config.get("record_path", "./data_logs")
        if hasattr(self.tab_control, "txt_rec_path"):
            self.tab_control.txt_rec_path.setText(rec_path)
        if hasattr(self.tab_control, "txt_rec_name"):
            self.tab_control.txt_rec_name.setText(new_config.get("record_filename", "saguling_mission"))
        if hasattr(self.tab_control, "sp_rec_interval") and "record_interval_s" in new_config:
            self.tab_control.sp_rec_interval.setValue(float(new_config["record_interval_s"]))

        # Synchronize Theme
        new_theme = new_config.get("theme", "Dark Mode")
        self.apply_theme(new_theme)

        self.tab_control.append_log("[CONFIG] Seluruh konfigurasi sistem GCS berhasil diperbarui & disimpan.")

    # =========================================================
    # --- OPERATING MODE & FOXGLOVE BRIDGE ---
    # =========================================================
    def on_operating_mode_changed(self, mode: str):
        self.adapter.set_operating_mode(mode)

    def toggle_foxglove_bridge(self, enable: bool):
        self.adapter.toggle_foxglove(enable)

    # =========================================================
    # --- NETWORK & TELEMETRY HANDLERS ---
    # =========================================================
    def toggle_network_connection(self):
        if self.adapter.is_connected():
            self.adapter.stop_connection()
        else:
            ip = self.config.get("target_ip", "192.168.1.170")
            port = int(self.config.get("target_port", 9000))
            proto = self.config.get("protocol", "TCP")
            self.connect_ethernet_target(ip, port, proto=proto)

    def connect_ethernet_target(self, ip: str, port: int, proto: str = "TCP"):
        self.tab_control.append_log(f"Menghubungkan ke Ethernet ({proto}) {ip}:{port}...")
        self.adapter.start_connection(conn_type=proto, ip=ip, port=port)

    def connect_usb_port(self, port: str, baud: int):
        self.tab_control.append_log(f"Membuka port serial USB {port} @ {baud} bps...")
        self.adapter.start_connection(conn_type="SERIAL", serial_port=port, baud=baud)

    def on_connection_changed(self, is_connected: bool, msg: str):
        self.action_bar.set_connection_status(is_connected, msg)
        self.tab_control.append_log(f"[KONEKSI] {msg}")

    def on_telemetry_received(self, data: Dict[str, Any]):
        # 1. Update Tab 1 Realtime metrics (Sensor cards, 3D attitude, Camera HUD, Thrusters)
        self.tab_control.update_telemetry(data)

        # 2. Update Tab 2 Mission Control (Depth, Yaw, Manual axes)
        if hasattr(self, "tab_mission") and hasattr(self.tab_mission, "update_telemetry"):
            self.tab_mission.update_telemetry(data)

        # 3. Update Tab 3 Multi-Graph Slots (always stream to buffers)
        self.tab_graphs.add_telemetry(data)

        # 4. Update Quick Action Bar
        self.action_bar.update_telemetry(data)

    # =========================================================
    # --- CSV RECORDING & TIMER ---
    # =========================================================
    def start_csv_recording(self):
        rec_path = self.tab_control.txt_rec_path.text().strip()
        rec_name = self.tab_control.txt_rec_name.text().strip()
        rec_interval = self.tab_control.get_recording_interval()
        filepath = self.adapter.start_recording(mission_name=rec_name, custom_dir=rec_path, interval=rec_interval)
        self.tab_control.set_recording_state(True)

    def stop_csv_recording(self):
        res = self.adapter.stop_recording()
        self.tab_control.set_recording_state(False)
        dur = res.get('duration_s', 0.0)
        QtWidgets.QMessageBox.information(
            self, "Record Selesai",
            f"Data telemetri berhasil direkam ke file:\n{res['file_path']}\n\nTotal data: {res['rows']} baris ({dur:.1f} detik)"
        )

    # =========================================================
    # --- DEADMAN SWITCH KEYBOARD 6-DOF CONTROLS ---
    # =========================================================
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if not self.tab_control.manual_mode_active:
            super().keyPressEvent(event)
            return

        if event.isAutoRepeat():
            return

        key = event.key()
        # 1. Surge (Maju/Mundur)
        if key == QtCore.Qt.Key_W:
            self.tab_control.start_6dof_motion("SURGE", 1)
            self.tab_control.append_log(">>> INPUT 6-DOF: W [TEKAN] -> Maju (Surge +1)")
            event.accept()
        elif key == QtCore.Qt.Key_S:
            self.tab_control.start_6dof_motion("SURGE", -1)
            self.tab_control.append_log(">>> INPUT 6-DOF: S [TEKAN] -> Mundur (Surge -1)")
            event.accept()

        # 2. Sway (Geser Kiri/Kanan)
        elif key == QtCore.Qt.Key_A:
            self.tab_control.start_6dof_motion("SWAY", -1)
            self.tab_control.append_log(">>> INPUT 6-DOF: A [TEKAN] -> Geser Kiri (Sway -1)")
            event.accept()
        elif key == QtCore.Qt.Key_D:
            self.tab_control.start_6dof_motion("SWAY", 1)
            self.tab_control.append_log(">>> INPUT 6-DOF: D [TEKAN] -> Geser Kanan (Sway +1)")
            event.accept()

        # 3. Heave (Naik/Turun)
        elif key == QtCore.Qt.Key_R:
            self.tab_control.start_6dof_motion("HEAVE", -1)
            self.tab_control.append_log(">>> INPUT 6-DOF: R [TEKAN] -> Naik (Heave -1)")
            event.accept()
        elif key == QtCore.Qt.Key_F:
            self.tab_control.start_6dof_motion("HEAVE", 1)
            self.tab_control.append_log(">>> INPUT 6-DOF: F [TEKAN] -> Turun (Heave +1)")
            event.accept()

        # 4. Yaw (Putar Haluan Kiri/Kanan)
        elif key == QtCore.Qt.Key_Q:
            self.tab_control.start_6dof_motion("YAW", -1)
            self.tab_control.append_log(">>> INPUT 6-DOF: Q [TEKAN] -> Putar Kiri (Yaw -1)")
            event.accept()
        elif key == QtCore.Qt.Key_E:
            self.tab_control.start_6dof_motion("YAW", 1)
            self.tab_control.append_log(">>> INPUT 6-DOF: E [TEKAN] -> Putar Kanan (Yaw +1)")
            event.accept()

        # 5. Pitch (Nose Up/Down)
        elif key in (QtCore.Qt.Key_I, QtCore.Qt.Key_Up):
            self.tab_control.start_6dof_motion("PITCH", 1)
            self.tab_control.append_log(">>> INPUT 6-DOF: I/Up [TEKAN] -> Nose Up (Pitch +1)")
            event.accept()
        elif key in (QtCore.Qt.Key_K, QtCore.Qt.Key_Down):
            self.tab_control.start_6dof_motion("PITCH", -1)
            self.tab_control.append_log(">>> INPUT 6-DOF: K/Down [TEKAN] -> Nose Down (Pitch -1)")
            event.accept()

        # 6. Roll (Miring Kiri/Kanan)
        elif key in (QtCore.Qt.Key_J, QtCore.Qt.Key_Left):
            self.tab_control.start_6dof_motion("ROLL", -1)
            self.tab_control.append_log(">>> INPUT 6-DOF: J/Left [TEKAN] -> Miring Kiri (Roll -1)")
            event.accept()
        elif key in (QtCore.Qt.Key_L, QtCore.Qt.Key_Right):
            self.tab_control.start_6dof_motion("ROLL", 1)
            self.tab_control.append_log(">>> INPUT 6-DOF: L/Right [TEKAN] -> Miring Kanan (Roll +1)")
            event.accept()

        # Stop All (Spacebar)
        elif key == QtCore.Qt.Key_Space:
            self.tab_control.stop_all_motion()
            self.tab_control.append_log(">>> INPUT 6-DOF: SPACE [TEKAN] -> STOP SEMUA GERAK")
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if not self.tab_control.manual_mode_active:
            super().keyReleaseEvent(event)
            return

        if event.isAutoRepeat():
            return

        key = event.key()
        if key in (QtCore.Qt.Key_W, QtCore.Qt.Key_S):
            self.tab_control.stop_6dof_motion("SURGE")
            self.tab_control.append_log(">>> INPUT 6-DOF: W/S [LEPAS] -> Surge Stop")
            event.accept()
        elif key in (QtCore.Qt.Key_A, QtCore.Qt.Key_D):
            self.tab_control.stop_6dof_motion("SWAY")
            self.tab_control.append_log(">>> INPUT 6-DOF: A/D [LEPAS] -> Sway Stop")
            event.accept()
        elif key in (QtCore.Qt.Key_R, QtCore.Qt.Key_F):
            self.tab_control.stop_6dof_motion("HEAVE")
            self.tab_control.append_log(">>> INPUT 6-DOF: R/F [LEPAS] -> Heave Stop")
            event.accept()
        elif key in (QtCore.Qt.Key_Q, QtCore.Qt.Key_E):
            self.tab_control.stop_6dof_motion("YAW")
            self.tab_control.append_log(">>> INPUT 6-DOF: Q/E [LEPAS] -> Yaw Stop")
            event.accept()
        elif key in (QtCore.Qt.Key_I, QtCore.Qt.Key_K, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            self.tab_control.stop_6dof_motion("PITCH")
            self.tab_control.append_log(">>> INPUT 6-DOF: Pitch Stop")
            event.accept()
        elif key in (QtCore.Qt.Key_J, QtCore.Qt.Key_L, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
            self.tab_control.stop_6dof_motion("ROLL")
            self.tab_control.append_log(">>> INPUT 6-DOF: Roll Stop")
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def on_joystick_motion(self, surge: int, sway: int, heave: int, yaw: int):
        self.adapter.send_command(f"STICK,{surge},{sway},{heave},{yaw}\n")

    def on_emergency_kill(self):
        reply = QtWidgets.QMessageBox.critical(
            self,
            "EMERGENCY KILL SWITCH",
            "Yakin ingin memutus TOTAL aliran daya ke seluruh motor thruster?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.adapter.emergency_kill()

    def on_safety_alert(self, level: str, title: str, description: str):
        clean_title = title.replace("_", " ")
        self.tab_control.append_log(f"[{level}] {clean_title}: {description}")

    def closeEvent(self, event):
        self.adapter.shutdown()
        if self.tab_control.widget_cam:
            self.tab_control.widget_cam.stop_camera()
        if self.tab_control.split_cam:
            self.tab_control.split_cam.stop_camera()
        event.accept()
