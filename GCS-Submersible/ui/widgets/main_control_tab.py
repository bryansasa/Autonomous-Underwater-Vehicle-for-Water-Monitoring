# -*- coding: utf-8 -*-
"""
Main Control & Data Recording Tab (Tab 1)
Features full 6 Degrees of Freedom (6-DOF) Manual Motion Controller:
  - Linear Translations: Surge (Forward/Backward), Sway (Strafe Left/Right), Heave (Up/Down)
  - Angular Rotations: Roll (Tilt Left/Right), Pitch (Nose Up/Down), Yaw (Turn Left/Right)
  - Navigation Views: 3D Model, 2D PFD HUD, Live Camera Feed, and Split View
  - Realtime Sensor Cards, LMPC Station-Keeping, and CSV Logging.
"""
import os
import re
from datetime import datetime
from typing import Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui

from ui.widgets.submersible_3d_widget import Submersible3DWidget
from ui.widgets.pfd_widget import PFDWidget
from ui.widgets.camera_feed_widget import CameraFeedWidget
from ui.widgets.thruster_matrix import ThrusterMatrix


# ──────────────────────────────────────────────
# Minimalist Industrial Matte Dark Palette (Red Accent)
# ──────────────────────────────────────────────
CLR_ACCENT = "#E53935"   # Industrial Red Accent
CLR_SUCCESS = "#D32F2F"  # Red (Replaced Green)
CLR_DANGER = "#C62828"   # Deep Red
CLR_WARNING = "#FF9800"  # Amber Orange
CLR_PURPLE = "#7B61FF"   # Soft Purple
CLR_MUTED = "#9E9E9E"    # Muted Gray
CLR_TEXT = "#E0E0E0"     # Primary Text



class MainControlTab(QtWidgets.QWidget):
    """
    Tab 1: 6-DOF Motion Control + 3D/2D Navigation + Realtime Data + CSV Logging.
    """
    command_generated = QtCore.pyqtSignal(str)
    start_recording_requested = QtCore.pyqtSignal()
    stop_recording_requested = QtCore.pyqtSignal()
    sd_download_requested = QtCore.pyqtSignal(str)
    theme_changed_signal = QtCore.pyqtSignal(str)
    connect_ethernet_requested = QtCore.pyqtSignal(str, int)
    connect_usb_requested = QtCore.pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manual_mode_active = False

        # Active motion states for 6-DOF
        self.motion_states = {
            "SURGE": 0,  # +1 Fwd, -1 Bwd
            "SWAY": 0,   # +1 Right, -1 Left
            "HEAVE": 0,  # +1 Down, -1 Up
            "ROLL": 0,   # +1 Right, -1 Left
            "PITCH": 0,  # +1 Up, -1 Down
            "YAW": 0,    # +1 Right, -1 Left
        }

        self.sensor_pills = []
        self.mini_tbm_boxes = []

        self.init_ui()

    def init_ui(self):
        root_layout = QtWidgets.QHBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(8)

        # ====================================================
        # KOLOM 1 (KIRI): NAVIGASI VISUAL & PENDORONG GAYA
        # ====================================================
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # 1. Navigation View Switcher (3D / 2D PFD / Camera / Split)
        nav_header = QtWidgets.QHBoxLayout()
        nav_header.setSpacing(6)

        self.lbl_nav_title = QtWidgets.QLabel("NAVIGASI & VISUAL:")
        self.lbl_nav_title.setStyleSheet(f"color: {CLR_ACCENT}; font-weight: bold; font-size: 11px;")
        nav_header.addWidget(self.lbl_nav_title)

        self.combo_nav_view = QtWidgets.QComboBox()
        self.combo_nav_view.addItems(["Orientasi 3D", "PFD Horizon 2D", "Live Camera Feed", "Split 3D + Kamera"])
        self.combo_nav_view.setStyleSheet("font-weight: bold; font-size: 11px; padding: 2px 8px;")
        self.combo_nav_view.currentIndexChanged.connect(self.on_nav_view_changed)
        nav_header.addWidget(self.combo_nav_view, stretch=1)

        left_layout.addLayout(nav_header)

        # 2. Stacked Navigation Widgets
        self.nav_stack = QtWidgets.QStackedWidget()
        self.nav_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Page 0: 3D Submersible Orientation
        self.widget_3d = Submersible3DWidget()
        self.nav_stack.addWidget(self.widget_3d)

        # Page 1: 2D PFD HUD
        self.widget_pfd = PFDWidget()
        self.nav_stack.addWidget(self.widget_pfd)

        # Page 2: Live Camera Feed
        self.widget_cam = CameraFeedWidget()
        self.nav_stack.addWidget(self.widget_cam)

        # Page 3: Split View (3D + Camera side by side)
        self.split_nav_widget = QtWidgets.QWidget()
        split_layout = QtWidgets.QVBoxLayout(self.split_nav_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(4)
        self.split_3d = Submersible3DWidget()
        self.split_3d.setMinimumSize(180, 110)
        self.split_cam = CameraFeedWidget()
        self.split_cam.setMinimumSize(180, 110)
        split_layout.addWidget(self.split_3d, stretch=1)
        split_layout.addWidget(self.split_cam, stretch=1)
        self.nav_stack.addWidget(self.split_nav_widget)

        left_layout.addWidget(self.nav_stack, stretch=1)

        # Thruster matrix cleaned from Tab 1 per user request
        self.thruster_matrix = None

        root_layout.addWidget(left_widget, stretch=4)

        # ====================================================
        # KOLOM 2 (TENGAH): DATA SENSOR REALTIME & KONTROL GERAK
        # ====================================================
        mid_widget = QtWidgets.QWidget()
        mid_layout = QtWidgets.QVBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(6)

        # 1. Data Sensor Realtime (Kapsul Pill - GUI Sebelumnya)
        grp_sensors = QtWidgets.QGroupBox("DATA SENSOR REALTIME")
        s_layout = QtWidgets.QVBoxLayout(grp_sensors)
        s_layout.setContentsMargins(8, 6, 8, 6)
        s_layout.setSpacing(4)

        # Sensor Pill Rows (Dual Battery & Saguling Telemetry)
        self.lbl_depth_val = self._create_sensor_pill("DEPTH", "0.00 m", s_layout)
        self.lbl_lmpc_err = self._create_sensor_pill("Deviasi Z", "0.00 m", s_layout)
        self.lbl_batt_val = self._create_sensor_pill("BATT THRUSTER", "0.00 V (100%)", s_layout)
        self.lbl_curr_val = self._create_sensor_pill("ARUS THRUSTER", "0.00 A", s_layout)
        self.lbl_sensor_batt_val = self._create_sensor_pill("BATT SENSOR", "0.00 V (100%)", s_layout)
        self.lbl_sensor_curr_val = self._create_sensor_pill("ARUS SENSOR", "0.00 A", s_layout)
        self.lbl_do_val = self._create_sensor_pill("DO", "0.00 mg/L", s_layout)
        self.lbl_ph_val = self._create_sensor_pill("pH", "0.00", s_layout)
        self.lbl_temp_val = self._create_sensor_pill("Temperature", "0.00 °C", s_layout)
        self.lbl_cond_val = self._create_sensor_pill("Conductivity", "0.0 µS/cm", s_layout)

        mid_layout.addWidget(grp_sensors)

        # 2. Kontrol Gerak Manual (6-DOF)
        grp_motion = QtWidgets.QGroupBox("KONTROL GERAK MANUAL (6-DOF)")
        gm_layout = QtWidgets.QVBoxLayout(grp_motion)
        gm_layout.setContentsMargins(8, 6, 8, 6)
        gm_layout.setSpacing(4)

        m_head = QtWidgets.QHBoxLayout()
        self.cb_manual_mode = QtWidgets.QCheckBox("Aktifkan Kontrol Keyboard")
        self.cb_manual_mode.setStyleSheet(f"color: {CLR_TEXT}; font-weight: bold; font-size: 11px;")
        self.cb_manual_mode.toggled.connect(self.on_toggle_manual_mode)
        m_head.addWidget(self.cb_manual_mode)

        self.lbl_motion_status = QtWidgets.QLabel("NETRAL (IDLE)")
        self.lbl_motion_status.setStyleSheet(f"color: {CLR_MUTED}; font-size: 10px; font-weight: bold;")
        self.lbl_motion_status.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        m_head.addWidget(self.lbl_motion_status)
        gm_layout.addLayout(m_head)

        # 6-DOF Sub-Tabs (Translasi & Rotasi)
        self.tabs_6dof = QtWidgets.QTabWidget()
        self.tabs_6dof.setStyleSheet("QTabBar::tab { font-size: 10px; font-weight: bold; padding: 3px 8px; }")

        # --- TAB A: TRANSLASI ---
        tab_trans = QtWidgets.QWidget()
        trans_layout = QtWidgets.QHBoxLayout(tab_trans)
        trans_layout.setContentsMargins(4, 4, 4, 4)
        trans_layout.setSpacing(6)

        dpad_grid = QtWidgets.QGridLayout()
        dpad_grid.setSpacing(3)

        self.btn_fwd = self._create_motion_button("MAJU [W]", CLR_SUCCESS, "SURGE", 1)
        self.btn_bwd = self._create_motion_button("MUNDUR [S]", CLR_WARNING, "SURGE", -1)
        self.btn_left = self._create_motion_button("GESER KIRI [A]", CLR_ACCENT, "SWAY", -1)
        self.btn_right = self._create_motion_button("GESER KANAN [D]", CLR_ACCENT, "SWAY", 1)
        self.btn_stop_trans = QtWidgets.QPushButton("STOP")
        self.btn_stop_trans.setStyleSheet(
            "background-color: #2A2F38; border: 1px solid #555B63; color: white; "
            "font-weight: bold; font-size: 10px; border-radius: 4px;"
        )
        self.btn_stop_trans.clicked.connect(self.stop_all_motion)

        dpad_grid.addWidget(self.btn_fwd, 0, 1)
        dpad_grid.addWidget(self.btn_left, 1, 0)
        dpad_grid.addWidget(self.btn_stop_trans, 1, 1)
        dpad_grid.addWidget(self.btn_right, 1, 2)
        dpad_grid.addWidget(self.btn_bwd, 2, 1)
        trans_layout.addLayout(dpad_grid, stretch=3)

        heave_box = QtWidgets.QVBoxLayout()
        heave_box.setSpacing(4)
        self.lbl_heave = QtWidgets.QLabel("Vertikal:")
        self.lbl_heave.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {CLR_MUTED};")
        self.lbl_heave.setAlignment(QtCore.Qt.AlignCenter)
        heave_box.addWidget(self.lbl_heave)

        self.btn_up = self._create_motion_button("NAIK [R]", CLR_SUCCESS, "HEAVE", -1)
        self.btn_down = self._create_motion_button("TURUN [F]", CLR_WARNING, "HEAVE", 1)
        heave_box.addWidget(self.btn_up)
        heave_box.addWidget(self.btn_down)
        trans_layout.addLayout(heave_box, stretch=2)

        self.tabs_6dof.addTab(tab_trans, "Translasi")

        # --- TAB B: ROTASI ---
        tab_rot = QtWidgets.QWidget()
        rot_layout = QtWidgets.QGridLayout(tab_rot)
        rot_layout.setContentsMargins(4, 4, 4, 4)
        rot_layout.setSpacing(4)

        self.btn_yaw_left = self._create_motion_button("PUTAR KIRI [Q]", CLR_ACCENT, "YAW", -1)
        self.btn_yaw_right = self._create_motion_button("PUTAR KANAN [E]", CLR_ACCENT, "YAW", 1)
        rot_layout.addWidget(self.btn_yaw_left, 0, 0)
        rot_layout.addWidget(self.btn_yaw_right, 0, 1)

        self.btn_pitch_up = self._create_motion_button("PITCH UP [I]", CLR_WARNING, "PITCH", 1)
        self.btn_pitch_down = self._create_motion_button("PITCH DOWN [K]", CLR_WARNING, "PITCH", -1)
        rot_layout.addWidget(self.btn_pitch_up, 1, 0)
        rot_layout.addWidget(self.btn_pitch_down, 1, 1)

        self.btn_roll_left = self._create_motion_button("ROLL KIRI [J]", CLR_PURPLE, "ROLL", -1)
        self.btn_roll_right = self._create_motion_button("ROLL KANAN [L]", CLR_PURPLE, "ROLL", 1)
        rot_layout.addWidget(self.btn_roll_left, 2, 0)
        rot_layout.addWidget(self.btn_roll_right, 2, 1)

        self.tabs_6dof.addTab(tab_rot, "Rotasi")
        gm_layout.addWidget(self.tabs_6dof)

        # Speed Row
        speed_row = QtWidgets.QHBoxLayout()
        speed_row.addWidget(QtWidgets.QLabel("Kecepatan:"))
        self.slider_speed = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_speed.setRange(50, 400)
        self.slider_speed.setValue(250)
        self.slider_speed.valueChanged.connect(self._on_slider_speed_changed)
        speed_row.addWidget(self.slider_speed)

        self.txt_speed = QtWidgets.QLineEdit("250")
        self.txt_speed.setFixedWidth(42)
        self.txt_speed.textChanged.connect(self._on_txt_speed_changed)
        speed_row.addWidget(self.txt_speed)

        self.btn_stop_all = QtWidgets.QPushButton("STOP [SPASI]")
        self.btn_stop_all.setObjectName("btnDanger")
        self.btn_stop_all.setStyleSheet("font-weight: bold; font-size: 10px; padding: 4px 8px;")
        self.btn_stop_all.clicked.connect(self.stop_all_motion)
        speed_row.addWidget(self.btn_stop_all)
        gm_layout.addLayout(speed_row)

        mid_layout.addWidget(grp_motion)

        # 3. Kendali Otomatis Depth Hold LMPC
        grp_lmpc = QtWidgets.QGroupBox("KENDALI OTOMATIS (DEPTH HOLD)")
        lmpc_layout = QtWidgets.QGridLayout(grp_lmpc)
        lmpc_layout.setContentsMargins(8, 6, 8, 6)
        lmpc_layout.setSpacing(4)

        self.cb_lmpc_hold = QtWidgets.QCheckBox("Auto Hold")
        self.cb_lmpc_hold.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        self.cb_lmpc_hold.toggled.connect(self.on_toggle_lmpc_hold)
        lmpc_layout.addWidget(self.cb_lmpc_hold, 0, 0)

        lmpc_layout.addWidget(QtWidgets.QLabel("Target (m):"), 0, 1)
        self.txt_setpoint_depth = QtWidgets.QLineEdit("1.5")
        self.txt_setpoint_depth.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.txt_setpoint_depth.setMinimumWidth(40)
        lmpc_layout.addWidget(self.txt_setpoint_depth, 0, 2)

        self.btn_send_setpoint = QtWidgets.QPushButton("Kirim")
        self.btn_send_setpoint.clicked.connect(self.on_send_setpoint)
        lmpc_layout.addWidget(self.btn_send_setpoint, 0, 3)

        lmpc_layout.addWidget(QtWidgets.QLabel("Np (Prediksi):"), 1, 0)
        self.txt_np = QtWidgets.QLineEdit("10")
        self.txt_np.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        lmpc_layout.addWidget(self.txt_np, 1, 1)

        lmpc_layout.addWidget(QtWidgets.QLabel("Nc (Kontrol):"), 1, 2)
        self.txt_nc = QtWidgets.QLineEdit("3")
        self.txt_nc.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        lmpc_layout.addWidget(self.txt_nc, 1, 3)

        self.btn_flash_lmpc = QtWidgets.QPushButton("Simpan Parameter")
        self.btn_flash_lmpc.clicked.connect(self.on_flash_lmpc)
        lmpc_layout.addWidget(self.btn_flash_lmpc, 2, 0, 1, 4)

        mid_layout.addWidget(grp_lmpc)

        # 4. Optimasi Daya & Sampling Adaptif (EA-DSRA)
        grp_dsra = QtWidgets.QGroupBox("OPTIMASI DAYA & SAMPLING (EA-DSRA)")
        dsra_layout = QtWidgets.QGridLayout(grp_dsra)
        dsra_layout.setContentsMargins(8, 6, 8, 6)
        dsra_layout.setSpacing(4)

        # Row 0: Mode Selector & Action
        dsra_layout.addWidget(QtWidgets.QLabel("Profil Sampling:"), 0, 0)
        self.combo_dsra_profile = QtWidgets.QComboBox()
        self.combo_dsra_profile.addItems([
            "Adaptif Otomatis (EA-DSRA)",
            "Frekuensi Tetap (1 Hz Baseline)",
            "Mode Hemat Baterai (Eco Mode)"
        ])
        self.combo_dsra_profile.setStyleSheet("font-size: 10px;")
        dsra_layout.addWidget(self.combo_dsra_profile, 0, 1, 1, 2)

        self.btn_apply_dsra_profile = QtWidgets.QPushButton("Terapkan")
        self.btn_apply_dsra_profile.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_apply_dsra_profile.clicked.connect(self.on_apply_dsra_profile)
        dsra_layout.addWidget(self.btn_apply_dsra_profile, 0, 3)

        # Row 1: Energy & Penalty Status Row
        self.pwr_status_frame = QtWidgets.QFrame()
        self.pwr_status_frame.setStyleSheet("background-color: #12151B; border: 1px solid #252A34; border-radius: 4px;")
        ps_layout = QtWidgets.QHBoxLayout(self.pwr_status_frame)
        ps_layout.setContentsMargins(6, 3, 6, 3)
        ps_layout.setSpacing(8)

        self.lbl_dsra_wea = QtWidgets.QLabel("Penalti Wea: 1.00x")
        self.lbl_dsra_wea.setStyleSheet("color: #00E5FF; font-size: 10px; font-weight: bold; font-family: 'Consolas', monospace;")
        ps_layout.addWidget(self.lbl_dsra_wea)

        self.lbl_dsra_savings = QtWidgets.QLabel("Hemat Daya: ~38.4%")
        self.lbl_dsra_savings.setStyleSheet("color: #00E676; font-size: 10px; font-weight: bold;")
        ps_layout.addWidget(self.lbl_dsra_savings)

        self.lbl_dsra_gating = QtWidgets.QLabel("Gating: Aktif")
        self.lbl_dsra_gating.setStyleSheet("color: #90A4AE; font-size: 10px;")
        ps_layout.addWidget(self.lbl_dsra_gating)

        dsra_layout.addWidget(self.pwr_status_frame, 1, 0, 1, 4)

        # Row 2: Live T_BM Sampling Intervals (Detik per sensor)
        tbm_grid = QtWidgets.QGridLayout()
        tbm_grid.setContentsMargins(0, 2, 0, 2)
        tbm_grid.setSpacing(4)

        self.lbl_tbm_temp = self._create_mini_tbm_box("Suhu", "3.0 s", tbm_grid, 0, 0)
        self.lbl_tbm_do = self._create_mini_tbm_box("DO", "2.0 s", tbm_grid, 0, 1)
        self.lbl_tbm_ph = self._create_mini_tbm_box("pH", "5.0 s", tbm_grid, 0, 2)
        self.lbl_tbm_cond = self._create_mini_tbm_box("EC", "4.0 s", tbm_grid, 0, 3)

        dsra_layout.addLayout(tbm_grid, 2, 0, 1, 4)

        # Row 3: Ambang Batas Kritis SoC
        dsra_layout.addWidget(QtWidgets.QLabel("Ambang SoC (%):"), 3, 0)
        self.sp_tab1_soc_th = QtWidgets.QDoubleSpinBox()
        self.sp_tab1_soc_th.setRange(5.0, 99.0)
        self.sp_tab1_soc_th.setValue(30.0)
        self.sp_tab1_soc_th.setToolTip("Batas kapasitas baterai untuk penghematan daya agresif. Naikkan (misal ke 90-95%) untuk menguji aktivasi penalti EA-DSRA seketika tanpa menunggu baterai habis.")
        dsra_layout.addWidget(self.sp_tab1_soc_th, 3, 1)

        self.btn_flash_dsra = QtWidgets.QPushButton("Kirim Parameter")
        self.btn_flash_dsra.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_flash_dsra.clicked.connect(self.on_flash_dsra)
        dsra_layout.addWidget(self.btn_flash_dsra, 3, 2, 1, 2)

        mid_layout.addWidget(grp_dsra)
        mid_layout.addStretch()

        mid_scroll = QtWidgets.QScrollArea()
        mid_scroll.setWidgetResizable(True)
        mid_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        mid_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        mid_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        mid_scroll.setWidget(mid_widget)

        root_layout.addWidget(mid_scroll, stretch=4)

        # ====================================================
        # KOLOM 3 (KANAN): PEREKAMAN DATA, KONEKSI & LOG SISTEM
        # ====================================================
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # 1. Perekaman Data CSV
        grp_rec = QtWidgets.QGroupBox("PEREKAMAN DATA CSV")
        gr_layout = QtWidgets.QVBoxLayout(grp_rec)
        gr_layout.setContentsMargins(8, 6, 8, 6)
        gr_layout.setSpacing(4)

        path_row = QtWidgets.QHBoxLayout()
        self.txt_rec_path = QtWidgets.QLineEdit("./data_logs")
        self.txt_rec_path.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.btn_browse_rec = QtWidgets.QPushButton("Browse")
        self.btn_browse_rec.clicked.connect(self.browse_rec_path)
        path_row.addWidget(self.txt_rec_path)
        path_row.addWidget(self.btn_browse_rec)
        gr_layout.addLayout(path_row)

        file_row = QtWidgets.QHBoxLayout()
        file_row.addWidget(QtWidgets.QLabel("File:"))
        self.txt_rec_name = QtWidgets.QLineEdit("record_saguling")
        self.txt_rec_name.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        file_row.addWidget(self.txt_rec_name)
        gr_layout.addLayout(file_row)

        # Row Interval Pengambilan / Rekam Data
        interval_row = QtWidgets.QHBoxLayout()
        self.lbl_interval = QtWidgets.QLabel("Interval:")
        self.lbl_interval.setStyleSheet("color: #C5CBD3; font-weight: 500;")
        interval_row.addWidget(self.lbl_interval)

        self.sp_rec_interval = QtWidgets.QDoubleSpinBox()
        self.sp_rec_interval.setRange(0.0, 3600.0)
        self.sp_rec_interval.setSingleStep(0.1)
        self.sp_rec_interval.setValue(1.0)
        self.sp_rec_interval.setDecimals(2)
        self.sp_rec_interval.setSuffix(" s")
        self.sp_rec_interval.setStyleSheet(
            "QDoubleSpinBox { background-color: #1A1A1A; color: #00E5FF; font-weight: bold; border: 1px solid #333333; border-radius: 3px; padding: 2px 4px; }"
        )
        self.sp_rec_interval.setToolTip("Interval waktu pencatatan data ke CSV.\n0.0 s = Simpan semua paket (~10 Hz / 100 ms)\n1.0 s = Simpan tiap 1 detik (1 Hz)\n0.5 s = Simpan tiap 500 ms (2 Hz)\n0.1 s = Simpan tiap 100 ms (10 Hz)")
        interval_row.addWidget(self.sp_rec_interval, stretch=1)

        self.cmb_interval_preset = QtWidgets.QComboBox()
        self.cmb_interval_preset.setStyleSheet(
            "QComboBox { background-color: #1A1A1A; color: #E0E0E0; border: 1px solid #333333; border-radius: 3px; padding: 2px 4px; }"
        )
        self.cmb_interval_preset.addItems([
            "Preset...",
            "100 ms (10 Hz)",
            "200 ms (5 Hz)",
            "500 ms (2 Hz)",
            "1.0 s (1 Hz)",
            "2.0 s (0.5 Hz)",
            "5.0 s (0.2 Hz)",
            "Semua Data (Raw 10Hz)"
        ])
        self.cmb_interval_preset.setToolTip("Pilih preset laju sampling pengambilan data cepat")
        self.cmb_interval_preset.currentIndexChanged.connect(self._on_interval_preset_changed)
        interval_row.addWidget(self.cmb_interval_preset, stretch=1)

        gr_layout.addLayout(interval_row)

        # Industrial Digital Clock
        self.timer_frame = QtWidgets.QFrame()
        self.timer_frame.setStyleSheet(
            "background-color: #101216; border: 1px solid #282C34; border-radius: 4px; padding: 4px;"
        )
        tf_layout = QtWidgets.QVBoxLayout(self.timer_frame)
        self.lbl_timer_pc = QtWidgets.QLabel("00:00:00")
        self.lbl_timer_pc.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_timer_pc.setStyleSheet(
            "color: #FF9800; font-size: 22px; font-weight: bold; font-family: 'Consolas', monospace; letter-spacing: 2px;"
        )
        tf_layout.addWidget(self.lbl_timer_pc)
        gr_layout.addWidget(self.timer_frame)

        btn_rec_box = QtWidgets.QHBoxLayout()
        self.btn_start_rec = QtWidgets.QPushButton("START RECORD")
        self.btn_start_rec.setObjectName("btnStart")
        self.btn_start_rec.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.btn_start_rec.setMinimumHeight(30)
        self.btn_start_rec.clicked.connect(self.start_recording_requested)

        self.btn_stop_rec = QtWidgets.QPushButton("STOP RECORD")
        self.btn_stop_rec.setObjectName("btnStop")
        self.btn_stop_rec.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.btn_stop_rec.setMinimumHeight(30)
        self.btn_stop_rec.setEnabled(False)
        self.btn_stop_rec.clicked.connect(self.stop_recording_requested)

        btn_rec_box.addWidget(self.btn_start_rec)
        btn_rec_box.addWidget(self.btn_stop_rec)
        gr_layout.addLayout(btn_rec_box)

        right_layout.addWidget(grp_rec)

        # 2. Pengaturan Jaringan & Tema
        grp_net = QtWidgets.QGroupBox("KONEKSI & TEMA")
        gn_layout = QtWidgets.QGridLayout(grp_net)
        gn_layout.setContentsMargins(8, 6, 8, 6)
        gn_layout.setSpacing(4)

        gn_layout.addWidget(QtWidgets.QLabel("IP Ethernet:"), 0, 0)
        self.txt_target_ip = QtWidgets.QLineEdit("192.168.1.170:9000")
        self.txt_target_ip.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.btn_set_ip = QtWidgets.QPushButton("Set & Konek")
        self.btn_set_ip.clicked.connect(self.on_set_target_ip)
        gn_layout.addWidget(self.txt_target_ip, 0, 1)
        gn_layout.addWidget(self.btn_set_ip, 0, 2)

        gn_layout.addWidget(QtWidgets.QLabel("Port USB:"), 1, 0)
        self.txt_usb_port = QtWidgets.QLineEdit("COM3")
        self.txt_usb_port.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.btn_connect_usb = QtWidgets.QPushButton("Konek USB")
        self.btn_connect_usb.clicked.connect(self.on_connect_usb)
        gn_layout.addWidget(self.txt_usb_port, 1, 1)
        gn_layout.addWidget(self.btn_connect_usb, 1, 2)

        gn_layout.addWidget(QtWidgets.QLabel("Tema GUI:"), 2, 0)
        self.combo_theme = QtWidgets.QComboBox()
        self.combo_theme.addItems(["Dark Mode", "Light Mode"])
        self.combo_theme.currentTextChanged.connect(self.theme_changed_signal.emit)
        gn_layout.addWidget(self.combo_theme, 2, 1, 1, 2)

        right_layout.addWidget(grp_net)

        # 3. Log Sistem Terminal
        grp_log = QtWidgets.QGroupBox("LOG SISTEM")
        log_box = QtWidgets.QVBoxLayout(grp_log)
        log_box.setContentsMargins(6, 4, 6, 4)
        log_box.setSpacing(4)

        self.txt_terminal = QtWidgets.QPlainTextEdit()
        self.txt_terminal.setReadOnly(True)
        self.txt_terminal.setMaximumBlockCount(500)
        log_box.addWidget(self.txt_terminal)

        btn_clr = QtWidgets.QPushButton("Clear Log")
        btn_clr.clicked.connect(self.txt_terminal.clear)
        log_box.addWidget(btn_clr)

        right_layout.addWidget(grp_log, stretch=1)
        root_layout.addWidget(right_widget, stretch=3)

    def _create_motion_button(self, label: str, clr: str, axis: str, direction: int) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(label)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        btn.setMinimumHeight(26)
        btn.setStyleSheet(
            f"background-color: {clr}; color: white; font-weight: bold; "
            f"font-size: 10px; border-radius: 4px;"
        )
        btn.pressed.connect(lambda: self.start_6dof_motion(axis, direction))
        btn.released.connect(lambda: self.stop_6dof_motion(axis))
        return btn

    def start_6dof_motion(self, axis: str, direction: int):
        if not self.manual_mode_active:
            return
        self.motion_states[axis] = direction
        self.command_generated.emit(f"{axis},{direction}\n")
        self.lbl_motion_status.setText(f"AKTIF: {axis} ({direction:+d})")
        self.lbl_motion_status.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: bold;")

    def stop_6dof_motion(self, axis: str):
        if not self.manual_mode_active:
            return
        self.motion_states[axis] = 0
        self.command_generated.emit(f"{axis},0\n")
        if all(v == 0 for v in self.motion_states.values()):
            self.lbl_motion_status.setText("NETRAL (IDLE)")
            self.lbl_motion_status.setStyleSheet("color: #CCCCCC; font-size: 10px; font-weight: bold;")

    def stop_all_motion(self):
        for k in self.motion_states:
            self.motion_states[k] = 0
        self.command_generated.emit("STOP_ALL\n")
        self.lbl_motion_status.setText("STOP TOTAL (0)")
        self.lbl_motion_status.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: bold;")

    def _on_slider_speed_changed(self, val: int):
        self.txt_speed.setText(str(val))
        self.command_generated.emit(f"SPEED,{val}\n")

    def _on_txt_speed_changed(self, text: str):
        try:
            val = int(text.strip())
            if 50 <= val <= 400:
                self.slider_speed.blockSignals(True)
                self.slider_speed.setValue(val)
                self.slider_speed.blockSignals(False)
                self.command_generated.emit(f"SPEED,{val}\n")
        except ValueError:
            pass

    def on_nav_view_changed(self, idx: int):
        self.nav_stack.setCurrentIndex(idx)

    def _create_sensor_toggle_btn(self, name: str, cmd_prefix: str, layout: QtWidgets.QBoxLayout) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(f"{name}: ON")
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn.setFixedHeight(22)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #15222E;
                border: 1px solid #00B0FF;
                color: #00E5FF;
                font-size: 9px;
                font-weight: 700;
                border-radius: 3px;
                padding: 1px 4px;
            }
            QPushButton:hover {
                background-color: #1C2D3D;
            }
            QPushButton:!checked {
                background-color: #1E1818;
                border: 1px solid #663333;
                color: #E57373;
            }
        """)
        btn.toggled.connect(lambda c: self._on_sensor_btn_toggled(btn, name, cmd_prefix, c))
        layout.addWidget(btn)
        return btn

    def _on_sensor_btn_toggled(self, btn: QtWidgets.QPushButton, name: str, cmd_prefix: str, checked: bool):
        btn.setText(f"{name}: ON" if checked else f"{name}: OFF")
        self.command_generated.emit(f"{cmd_prefix},{'1' if checked else '0'}\n")

    def _on_dsra_toggled(self, checked: bool):
        self.btn_dsra_mode.setText("DSRA: AKTIF" if checked else "DSRA: NONAKTIF")
        self.command_generated.emit(f"DSRA_MODE,{'1' if checked else '0'}\n")

    def _create_sensor_pill(self, title: str, default_val: str, layout: QtWidgets.QBoxLayout) -> QtWidgets.QLabel:
        """
        Creates a clean horizontal capsule pill row fitted to container width:
        [ ( TITLE ) ]  ----  [ ( VALUE ) ]
        """
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(4, 1, 4, 1)
        row.setSpacing(8)

        # 1. Parameter Label Capsule (Left Pill) - Fitted Expanding
        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        lbl_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        lbl_title.setFixedHeight(24)
        lbl_title.setStyleSheet("""
            QLabel {
                background-color: #141722;
                border: 1px solid #232a3c;
                border-radius: 4px;
                color: #94a3b8;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.3px;
                padding: 1px 6px;
            }
        """)

        # 2. Realtime Telemetry Value Capsule (Right Pill) - Fitted Expanding
        lbl_val = QtWidgets.QLabel(default_val)
        lbl_val.setAlignment(QtCore.Qt.AlignCenter)
        lbl_val.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        lbl_val.setFixedHeight(24)
        lbl_val.setStyleSheet("""
            QLabel {
                background-color: #10121a;
                border: 1px solid #1c2230;
                border-radius: 4px;
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                font-family: 'Consolas', monospace;
                padding: 1px 6px;
            }
        """)

        row.addWidget(lbl_title, stretch=4)
        row.addWidget(lbl_val, stretch=5)
        layout.addLayout(row)
        if not hasattr(self, "sensor_pills"):
            self.sensor_pills = []
        self.sensor_pills.append((lbl_title, lbl_val))
        return lbl_val

    def _create_sensor_card(self, title: str, default_val: str, grid: QtWidgets.QGridLayout, r: int, c: int) -> QtWidgets.QLabel:
        frame = QtWidgets.QFrame()
        frame.setObjectName("hudCard")
        frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        f_layout = QtWidgets.QVBoxLayout(frame)
        f_layout.setContentsMargins(6, 4, 6, 4)
        f_layout.setSpacing(2)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("color: #CCCCCC; font-size: 10px; font-weight: 700;")
        f_layout.addWidget(lbl_title)

        lbl_val = QtWidgets.QLabel(default_val)
        lbl_val.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: 800;")
        f_layout.addWidget(lbl_val)

        grid.addWidget(frame, r, c)
        return lbl_val

    def _create_mini_tbm_box(self, label: str, default_val: str, layout: QtWidgets.QGridLayout, row: int, col: int) -> QtWidgets.QLabel:
        box = QtWidgets.QFrame()
        box.setStyleSheet("background-color: #12151B; border: 1px solid #252A34; border-radius: 3px; padding: 2px;")
        b_layout = QtWidgets.QVBoxLayout(box)
        b_layout.setContentsMargins(4, 2, 4, 2)
        b_layout.setSpacing(1)

        lbl_hdr = QtWidgets.QLabel(f"TBM {label}")
        lbl_hdr.setStyleSheet("color: #8A99AD; font-size: 9px; font-weight: bold;")
        lbl_hdr.setAlignment(QtCore.Qt.AlignCenter)
        b_layout.addWidget(lbl_hdr)

        lbl_val = QtWidgets.QLabel(default_val)
        lbl_val.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold; font-family: 'Consolas', monospace;")
        lbl_val.setAlignment(QtCore.Qt.AlignCenter)
        b_layout.addWidget(lbl_val)

        layout.addWidget(box, row, col)
        if not hasattr(self, "mini_tbm_boxes"):
            self.mini_tbm_boxes = []
        self.mini_tbm_boxes.append((box, lbl_hdr, lbl_val))
        return lbl_val

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name

        # 1. Nav Title
        if hasattr(self, "lbl_nav_title"):
            self.lbl_nav_title.setStyleSheet(f"color: {CLR_ACCENT}; font-weight: bold; font-size: 11px;")

        # 2. Checkboxes & Status
        if hasattr(self, "cb_manual_mode"):
            self.cb_manual_mode.setStyleSheet(f"color: {'#E0E0E0' if is_dark else '#0F172A'}; font-weight: bold; font-size: 11px;")
        if hasattr(self, "cb_lmpc_hold"):
            self.cb_lmpc_hold.setStyleSheet(f"font-weight: bold; color: {'#FFFFFF' if is_dark else '#0F172A'};")
        if hasattr(self, "lbl_motion_status"):
            self.lbl_motion_status.setStyleSheet(f"color: {'#9E9E9E' if is_dark else '#64748B'}; font-size: 10px; font-weight: bold;")
        if hasattr(self, "lbl_heave"):
            self.lbl_heave.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {'#9E9E9E' if is_dark else '#64748B'};")
        if hasattr(self, "lbl_interval"):
            self.lbl_interval.setStyleSheet(f"color: {'#C5CBD3' if is_dark else '#334155'}; font-weight: 500;")

        # 3. Sensor Pills
        if hasattr(self, "sensor_pills"):
            for lbl_title, lbl_val in self.sensor_pills:
                if is_dark:
                    lbl_title.setStyleSheet("""
                        QLabel {
                            background-color: #141722;
                            border: 1px solid #232a3c;
                            border-radius: 4px;
                            color: #94a3b8;
                            font-size: 10px;
                            font-weight: 600;
                            letter-spacing: 0.3px;
                            padding: 1px 6px;
                        }
                    """)
                    lbl_val.setStyleSheet("""
                        QLabel {
                            background-color: #10121a;
                            border: 1px solid #1c2230;
                            border-radius: 4px;
                            color: #38bdf8;
                            font-size: 11px;
                            font-weight: 700;
                            font-family: 'Consolas', monospace;
                            padding: 1px 6px;
                        }
                    """)
                else:
                    lbl_title.setStyleSheet("""
                        QLabel {
                            background-color: #f1f5f9;
                            border: 1px solid #cbd5e1;
                            border-radius: 4px;
                            color: #334155;
                            font-size: 10px;
                            font-weight: 600;
                            letter-spacing: 0.3px;
                            padding: 1px 6px;
                        }
                    """)
                    lbl_val.setStyleSheet("""
                        QLabel {
                            background-color: #ffffff;
                            border: 1px solid #cbd5e1;
                            border-radius: 4px;
                            color: #0284c7;
                            font-size: 11px;
                            font-weight: 700;
                            font-family: 'Consolas', monospace;
                            padding: 1px 6px;
                        }
                    """)

        # 4. EA-DSRA Power Status Bar
        if hasattr(self, "pwr_status_frame"):
            if is_dark:
                self.pwr_status_frame.setStyleSheet("background-color: #12151B; border: 1px solid #252A34; border-radius: 4px;")
                self.lbl_dsra_wea.setStyleSheet("color: #00E5FF; font-size: 10px; font-weight: bold; font-family: 'Consolas', monospace;")
                self.lbl_dsra_savings.setStyleSheet("color: #00E676; font-size: 10px; font-weight: bold;")
                self.lbl_dsra_gating.setStyleSheet("color: #90A4AE; font-size: 10px;")
            else:
                self.pwr_status_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px;")
                self.lbl_dsra_wea.setStyleSheet("color: #0284c7; font-size: 10px; font-weight: bold; font-family: 'Consolas', monospace;")
                self.lbl_dsra_savings.setStyleSheet("color: #16a34a; font-size: 10px; font-weight: bold;")
                self.lbl_dsra_gating.setStyleSheet("color: #64748b; font-size: 10px;")

        # 5. Mini TBM Boxes
        if hasattr(self, "mini_tbm_boxes"):
            for box, lbl_hdr, lbl_val in self.mini_tbm_boxes:
                if is_dark:
                    box.setStyleSheet("background-color: #12151B; border: 1px solid #252A34; border-radius: 3px; padding: 2px;")
                    lbl_hdr.setStyleSheet("color: #8A99AD; font-size: 9px; font-weight: bold;")
                    lbl_val.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold; font-family: 'Consolas', monospace;")
                else:
                    box.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 3px; padding: 2px;")
                    lbl_hdr.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
                    lbl_val.setStyleSheet("color: #0f172a; font-size: 11px; font-weight: bold; font-family: 'Consolas', monospace;")

        # 6. Digital Clock
        if hasattr(self, "timer_frame"):
            if is_dark:
                self.timer_frame.setStyleSheet("background-color: #101216; border: 1px solid #282C34; border-radius: 4px; padding: 4px;")
                self.lbl_timer_pc.setStyleSheet("color: #FF9800; font-size: 22px; font-weight: bold; font-family: 'Consolas', monospace; letter-spacing: 2px;")
            else:
                self.timer_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px;")
                self.lbl_timer_pc.setStyleSheet("color: #d97706; font-size: 22px; font-weight: bold; font-family: 'Consolas', monospace; letter-spacing: 2px;")

        # 7. Interval Inputs
        if hasattr(self, "sp_rec_interval"):
            if is_dark:
                self.sp_rec_interval.setStyleSheet("QDoubleSpinBox { background-color: #1A1A1A; color: #00E5FF; font-weight: bold; border: 1px solid #333333; border-radius: 3px; padding: 2px 4px; }")
                self.cmb_interval_preset.setStyleSheet("QComboBox { background-color: #1A1A1A; color: #E0E0E0; border: 1px solid #333333; border-radius: 3px; padding: 2px 4px; }")
            else:
                self.sp_rec_interval.setStyleSheet("QDoubleSpinBox { background-color: #FFFFFF; color: #0284c7; font-weight: bold; border: 1px solid #cbd5e1; border-radius: 3px; padding: 2px 4px; }")
                self.cmb_interval_preset.setStyleSheet("QComboBox { background-color: #FFFFFF; color: #0F172A; border: 1px solid #cbd5e1; border-radius: 3px; padding: 2px 4px; }")

        # 8. Child Components
        if getattr(self, "thruster_matrix", None) is not None:
            self.thruster_matrix.apply_theme(theme_name)
        if hasattr(self, "widget_3d"):
            self.widget_3d.set_theme(theme_name)
        if hasattr(self, "split_3d"):
            self.split_3d.set_theme(theme_name)


    def browse_rec_path(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Pilih Folder Penyimpanan CSV")
        if directory:
            self.txt_rec_path.setText(directory)

    def on_set_target_ip(self):
        text = self.txt_target_ip.text().strip()
        if ":" in text:
            ip, port = text.split(":")
            self.connect_ethernet_requested.emit(ip.strip(), int(port.strip()))

    def on_connect_usb(self):
        port = self.txt_usb_port.text().strip()
        if port.upper().startswith("COM"):
            port = port.upper()
        self.connect_usb_requested.emit(port, 115200)

    def on_toggle_manual_mode(self, checked: bool):
        self.manual_mode_active = checked
        if checked:
            self.cb_manual_mode.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 11px;")
            self.command_generated.emit("MANUAL,ON\n")
            self.lbl_motion_status.setText("MANUAL 6-DOF SIAP")
            self.setFocus()
        else:
            self.cb_manual_mode.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 11px;")
            self.command_generated.emit("MANUAL,OFF\n")
            self.stop_all_motion()

    def on_toggle_lmpc_hold(self, checked: bool):
        if checked:
            sp = self.txt_setpoint_depth.text().strip()
            self.command_generated.emit("LMPC_CONTROL,ON\n")
            if sp:
                self.command_generated.emit(f"SETPOINT,{sp}\n")
        else:
            self.command_generated.emit("LMPC_CONTROL,OFF\n")

    def on_send_setpoint(self):
        sp = self.txt_setpoint_depth.text().strip()
        if sp:
            self.command_generated.emit(f"SETPOINT,{sp}\n")

    def on_flash_lmpc(self):
        np_val = self.txt_np.text().strip()
        nc_val = self.txt_nc.text().strip()
        self.command_generated.emit(f"LMPC_PARAM,{np_val},{nc_val},100.0,0.1\n")

    def on_apply_dsra_profile(self):
        mode_idx = self.combo_dsra_profile.currentIndex()
        if mode_idx == 0:
            self.command_generated.emit("DSRA_MODE,1\n")
            self.command_generated.emit("DSRA_PROFILE,AUTO\n")
            self.append_log("[EA-DSRA] Mode Sampling Adaptif Otomatis Aktif.")
        elif mode_idx == 1:
            self.command_generated.emit("DSRA_MODE,0\n")
            self.command_generated.emit("DSRA_PROFILE,FIXED\n")
            self.append_log("[EA-DSRA] Mode Frekuensi Tetap 1 Hz (Baseline) Aktif.")
        else:
            self.command_generated.emit("DSRA_MODE,1\n")
            self.command_generated.emit("DSRA_PROFILE,ECO\n")
            self.append_log("[EA-DSRA] Mode Hemat Baterai (Eco Mode) Aktif.")

    def on_flash_dsra(self):
        soc_th = self.sp_tab1_soc_th.value()
        self.command_generated.emit(f"EADSRA_PARAM,PH,0.050,300,{soc_th:.1f}\n")
        self.append_log(f"[EA-DSRA] Parameter ambang batas baterai ({soc_th:.1f}%) dikirim ke wahana.")


    def append_log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        clean_text = re.sub(r'<[^>]+>', '', text)
        self.txt_terminal.appendPlainText(f"[{ts}] {clean_text}")

    def update_telemetry(self, data: Dict[str, Any]):
        depth = data.get("depth", 0.0)
        target_d = data.get("target_depth", float(self.txt_setpoint_depth.text() or 1.5))
        do_val = data.get("do", 0.0)
        ph = data.get("ph", 0.0)
        temp = data.get("temp", 0.0)
        cond = data.get("cond", 0.0)
        batt_v = data.get("battery_v", 0.0)
        soc = data.get("soc_kalman", data.get("soc", 100.0))
        curr_a = data.get("current_a", 0.0)
        sensor_batt_v = data.get("sensor_battery_v", 12.0)
        sensor_soc = data.get("sensor_soc", 100.0)
        sensor_curr_a = data.get("sensor_current_a", 0.0)
        err_d = abs(depth - target_d)
        pwms = data.get("pwms", [data.get(f"pwm{i}", 1500) for i in range(1, 7)])

        # Update text labels
        self.lbl_depth_val.setText(f"{depth:.2f} m")
        self.lbl_lmpc_err.setText(f"{err_d:.2f} m")
        self.lbl_batt_val.setText(f"{batt_v:.2f} V ({soc:.0f}%)")
        self.lbl_curr_val.setText(f"{curr_a:.2f} A")
        self.lbl_sensor_batt_val.setText(f"{sensor_batt_v:.2f} V ({sensor_soc:.0f}%)")
        self.lbl_sensor_curr_val.setText(f"{sensor_curr_a:.2f} A")
        self.lbl_do_val.setText(f"{do_val:.2f} mg/L")
        self.lbl_ph_val.setText(f"{ph:.2f}")
        self.lbl_temp_val.setText(f"{temp:.2f} °C")
        self.lbl_cond_val.setText(f"{cond:.1f} µS/cm")

        # Update 3D Submersible Orientation Widget
        self.widget_3d.update_attitude(
            roll=data.get("roll", 0.0),
            pitch=data.get("pitch", 0.0),
            yaw=data.get("yaw", 0.0),
            depth=depth,
            target_depth=target_d,
            pwms=pwms
        )
        self.split_3d.update_attitude(
            roll=data.get("roll", 0.0),
            pitch=data.get("pitch", 0.0),
            yaw=data.get("yaw", 0.0),
            depth=depth,
            target_depth=target_d,
            pwms=pwms
        )

        # Update PFD 2D Widget
        self.widget_pfd.update_attitude(
            roll=data.get("roll", 0.0),
            pitch=data.get("pitch", 0.0),
            yaw=data.get("yaw", 0.0),
            depth=depth,
            target_depth=target_d,
            target_yaw=data.get("target_yaw", 0.0),
            disturb_surge=data.get("disturb_surge", 0.0),
            disturb_sway=data.get("disturb_sway", 0.0)
        )

        # Update Live Camera HUD
        self.widget_cam.update_telemetry(data)
        self.split_cam.update_telemetry(data)

        # Update 6-Thruster Matrix (if present)
        if getattr(self, "thruster_matrix", None) is not None:
            self.thruster_matrix.update_telemetry(data)

        # Update EA-DSRA Live Telemetry Indicators
        if hasattr(self, "lbl_tbm_temp"):
            t_temp = data.get("tbm_temp", 3.0)
            t_ph = data.get("tbm_ph", 5.0)
            t_do = data.get("tbm_do", 2.0)
            t_cond = data.get("tbm_cond", 4.0)

            self.lbl_tbm_temp.setText(f"{t_temp:.1f} s")
            self.lbl_tbm_ph.setText(f"{t_ph:.1f} s")
            self.lbl_tbm_do.setText(f"{t_do:.1f} s")
            self.lbl_tbm_cond.setText(f"{t_cond:.1f} s")

            soc_th = self.sp_tab1_soc_th.value()
            wea = max(1.0, soc_th / max(1.0, soc)) if soc <= soc_th else 1.0
            self.lbl_dsra_wea.setText(f"Penalti Wea: {wea:.2f}x")

            avg_tbm = (t_temp + t_ph + t_do + t_cond) / 4.0
            savings_pct = max(0.0, min(85.0, (1.0 - (1.0 / max(1.0, avg_tbm))) * 100.0))
            self.lbl_dsra_savings.setText(f"Hemat Daya: ~{savings_pct:.1f}%")


    def _on_interval_preset_changed(self, index: int):
        mapping = {
            1: 0.10,  # 100 ms
            2: 0.20,  # 200 ms
            3: 0.50,  # 500 ms
            4: 1.00,  # 1.0 s
            5: 2.00,  # 2.0 s
            6: 5.00,  # 5.0 s
            7: 0.00,  # Semua Data (Raw 10Hz)
        }
        if index in mapping:
            self.sp_rec_interval.setValue(mapping[index])

    def get_recording_interval(self) -> float:
        return float(self.sp_rec_interval.value())

    def set_recording_state(self, is_recording: bool):
        self.btn_start_rec.setEnabled(not is_recording)
        self.btn_stop_rec.setEnabled(is_recording)
        self.sp_rec_interval.setEnabled(not is_recording)
        self.cmb_interval_preset.setEnabled(not is_recording)
        self.txt_rec_name.setEnabled(not is_recording)
        self.txt_rec_path.setEnabled(not is_recording)
        self.btn_browse_rec.setEnabled(not is_recording)

    def set_recording_timer_text(self, text: str):
        self.lbl_timer_pc.setText(text)
