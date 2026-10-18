# -*- coding: utf-8 -*-
"""
Quick Action & Top Status Bar for Submersible GCS
Includes:
  - Real Hardware vs Dummy Simulation Mode Switcher
  - Foxglove Studio WebSocket Bridge Status & Toggle
  - Arm / Disarm, Flight Mode Selector, Battery & Depth Readout, and Emergency Kill.
"""
import os
from typing import Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui


class QuickActionBar(QtWidgets.QFrame):
    """
    Top status and action toolbar modeled after modern robotics Mission Control.
    """
    mode_changed = QtCore.pyqtSignal(str)
    arm_state_changed = QtCore.pyqtSignal(bool)
    emergency_kill_triggered = QtCore.pyqtSignal()
    connect_requested = QtCore.pyqtSignal()
    operating_mode_changed = QtCore.pyqtSignal(str)  # "REAL" or "SIMULATION"
    foxglove_toggle_requested = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hudCard")
        self.setMinimumHeight(48)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.is_armed = False
        self.foxglove_active = False
        self.dividers = []

        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        # 1. SPELL Laboratory Logo & Vehicle Brand
        self.lbl_spell_logo = QtWidgets.QLabel()
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logo spell putih back.png"))
        if not os.path.exists(logo_path):
            logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo_spell.png"))
        if not os.path.exists(logo_path) and hasattr(sys, '_MEIPASS'):
            logo_path = os.path.join(sys._MEIPASS, "assets", "logo_spell.png")
        if os.path.exists(logo_path):
            pix = QtGui.QPixmap(logo_path).scaledToHeight(28, QtCore.Qt.SmoothTransformation)
            self.lbl_spell_logo.setPixmap(pix)
            self.lbl_spell_logo.setToolTip("SPELL Laboratory - Telkom University")
            layout.addWidget(self.lbl_spell_logo)

        self.lbl_logo = QtWidgets.QLabel("TYRANT-AQ")
        self.lbl_logo.setObjectName("vehicleLogo")
        self.lbl_logo.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(self.lbl_logo)

        self.lbl_sub = QtWidgets.QLabel("AUV GCS")
        self.lbl_sub.setStyleSheet("color: #CCCCCC; font-size: 10px; font-weight: 700;")
        layout.addWidget(self.lbl_sub)

        layout.addWidget(self._make_divider())

        # 2. Operating Mode Switcher (Real Hardware vs Dummy Simulation)
        layout.addWidget(QtWidgets.QLabel("MODE:"))
        self.combo_op_mode = QtWidgets.QComboBox()
        self.combo_op_mode.addItems(["SIMULASI (DUMMY)", "REAL (HARDWARE)"])
        self.combo_op_mode.setStyleSheet("font-weight: bold; padding: 3px 6px; font-size: 11px;")
        self.combo_op_mode.currentIndexChanged.connect(self._on_op_mode_changed)
        layout.addWidget(self.combo_op_mode)

        # Connection Status Indicator
        self.lbl_link_status = QtWidgets.QLabel("SIMULASI")
        self._set_link_badge("SIMULASI", "nominal")
        layout.addWidget(self.lbl_link_status)

        self.btn_connect = QtWidgets.QPushButton("CONNECT")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setFixedHeight(28)
        self.btn_connect.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.btn_connect.clicked.connect(self.connect_requested)
        layout.addWidget(self.btn_connect)

        layout.addWidget(self._make_divider())

        # 3. Foxglove Studio Bridge Button
        self.btn_foxglove = QtWidgets.QPushButton("Foxglove: OFF")
        self.btn_foxglove.setFixedHeight(28)
        self._set_foxglove_style(False)
        self.btn_foxglove.clicked.connect(self.toggle_foxglove)
        layout.addWidget(self.btn_foxglove)

        layout.addWidget(self._make_divider())

        # 4. Flight Mode Selector Combo
        layout.addWidget(QtWidgets.QLabel("NAV:"))
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["LMPC AUTO", "MANUAL", "DEPTH HOLD", "SURFACE"])
        self.combo_mode.setFixedHeight(28)
        self.combo_mode.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.combo_mode.currentTextChanged.connect(self.mode_changed.emit)
        layout.addWidget(self.combo_mode)

        # 5. ARM / DISARM Button
        self.btn_arm = QtWidgets.QPushButton("ARMED")
        self.btn_arm.setFixedHeight(28)
        self.is_armed = True
        self._set_arm_style(True)
        self.btn_arm.clicked.connect(self.toggle_arm)
        layout.addWidget(self.btn_arm)

        layout.addWidget(self._make_divider())

        # 6. Battery & Depth Mini Readouts (Dual Battery: Thruster + Sensor)
        self.lbl_batt = QtWidgets.QLabel("BATT [T: 24.8V | S: 12.1V]")
        self.lbl_batt.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_batt)

        self.lbl_depth_mini = QtWidgets.QLabel("Z: 0.00m")
        self.lbl_depth_mini.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_depth_mini)

        layout.addStretch()

        # 7. Emergency Kill Switch
        self.btn_kill = QtWidgets.QPushButton("EMERGENCY KILL")
        self.btn_kill.setObjectName("btnKill")
        self.btn_kill.setFixedHeight(30)
        self.btn_kill.setStyleSheet("font-size: 11px; font-weight: 900; padding: 2px 14px;")
        self.btn_kill.clicked.connect(self.emergency_kill_triggered)
        layout.addWidget(self.btn_kill)

    def _make_divider(self) -> QtWidgets.QFrame:
        div = QtWidgets.QFrame()
        div.setFrameShape(QtWidgets.QFrame.VLine)
        div.setFrameShadow(QtWidgets.QFrame.Sunken)
        div.setStyleSheet("color: #333333;")
        self.dividers.append(div)
        return div

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name
        if is_dark:
            self.lbl_logo.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 900; letter-spacing: 1px;")
            self.lbl_sub.setStyleSheet("color: #CCCCCC; font-size: 10px; font-weight: 700;")
            self.lbl_batt.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 11px;")
            self.lbl_depth_mini.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 11px;")
            for d in self.dividers:
                d.setStyleSheet("color: #333333;")
        else:
            self.lbl_logo.setStyleSheet("color: #0F172A; font-size: 14px; font-weight: 900; letter-spacing: 1px;")
            self.lbl_sub.setStyleSheet("color: #475569; font-size: 10px; font-weight: 700;")
            self.lbl_batt.setStyleSheet("color: #0F172A; font-weight: bold; font-size: 11px;")
            self.lbl_depth_mini.setStyleSheet("color: #0F172A; font-weight: bold; font-size: 11px;")
            for d in self.dividers:
                d.setStyleSheet("color: #D1D5DB;")

    def _set_link_badge(self, text: str, level: str):
        """Set the link status badge with white text on red/dark background."""
        borders = {
            "nominal": ("#D32F2F", "#B71C1C"),
            "danger":  ("#8E0000", "#5C0000"),
            "info":    ("#333333", "#444444"),
        }
        bg, border = borders.get(level, borders["nominal"])
        self.lbl_link_status.setText(text)
        self.lbl_link_status.setStyleSheet(
            f"background-color: {bg}; color: #FFFFFF; border: 1px solid {border}; "
            f"border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 11px;"
        )

    def _set_foxglove_style(self, active: bool):
        if active:
            self.btn_foxglove.setStyleSheet(
                "background-color: #D32F2F; border: 1px solid #B71C1C; "
                "color: #FFFFFF; font-weight: bold; font-size: 11px; padding: 2px 8px; border-radius: 4px;"
            )
        else:
            self.btn_foxglove.setStyleSheet(
                "background-color: #333333; border: 1px solid #444444; "
                "color: #FFFFFF; font-weight: bold; font-size: 11px; padding: 2px 8px; border-radius: 4px;"
            )

    def _set_arm_style(self, armed: bool):
        if armed:
            self.btn_arm.setStyleSheet(
                "background-color: #D32F2F; color: white; font-weight: 800; "
                "font-size: 11px; border-radius: 4px; padding: 2px 10px; border: 1px solid #B71C1C;"
            )
        else:
            self.btn_arm.setStyleSheet(
                "background-color: #333333; border: 1px solid #444444; "
                "color: #A0A0A0; font-weight: 800; font-size: 11px; border-radius: 4px; padding: 2px 10px;"
            )

    def _on_op_mode_changed(self, idx: int):
        mode_str = "SIMULATION" if idx == 0 else "REAL"
        self.operating_mode_changed.emit(mode_str)
        if mode_str == "SIMULATION":
            self._set_link_badge("SIMULASI", "nominal")
            self.btn_connect.setEnabled(False)
        else:
            self._set_link_badge("OFFLINE", "danger")
            self.btn_connect.setEnabled(True)

    def toggle_foxglove(self):
        self.foxglove_active = not self.foxglove_active
        if self.foxglove_active:
            self.btn_foxglove.setText("Foxglove: ON (:8765)")
            self._set_foxglove_style(True)
        else:
            self.btn_foxglove.setText("Foxglove: OFF")
            self._set_foxglove_style(False)
        self.foxglove_toggle_requested.emit(self.foxglove_active)

    def set_connection_status(self, connected: bool, message: str = ""):
        if "Simulasi" in message:
            self._set_link_badge("SIMULASI", "nominal")
            self.btn_connect.setText("CONNECT")
        elif connected:
            self._set_link_badge("HARDWARE ON", "nominal")
            self.btn_connect.setText("DISCONNECT")
        else:
            self._set_link_badge("OFFLINE", "danger")
            self.btn_connect.setText("CONNECT")

    def toggle_arm(self):
        self.is_armed = not self.is_armed
        if self.is_armed:
            self.btn_arm.setText("ARMED")
            self._set_arm_style(True)
        else:
            self.btn_arm.setText("DISARMED")
            self._set_arm_style(False)
        self.arm_state_changed.emit(self.is_armed)

    def update_telemetry(self, data: Dict[str, Any]):
        batt_v = data.get("battery_v", 24.0)
        soc = data.get("soc_kalman", data.get("soc", 100.0))
        sensor_v = data.get("sensor_battery_v", 12.0)
        depth = data.get("depth", 0.0)
        self.lbl_batt.setText(f"BATT [T: {batt_v:.1f}V ({soc:.0f}%) | S: {sensor_v:.1f}V]")
        self.lbl_depth_mini.setText(f"Z: {depth:.2f}m")
