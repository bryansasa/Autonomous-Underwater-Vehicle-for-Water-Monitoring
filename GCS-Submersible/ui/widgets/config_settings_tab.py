# -*- coding: utf-8 -*-
"""
Configuration & System Parameter Tuning Tab for Submersible Ground Control Station.
Enables comprehensive viewing, dynamic tuning, profile import/export,
and JSON file persistence for all AUV parameters (Network, LMPC, EA-DSRA, Safety, Joystick).
Redesigned with clear human-friendly labels, intuitive tooltips, and no emojis.
"""
import os
import json
import copy
from typing import Dict, Any, Optional

from PyQt5 import QtWidgets, QtCore, QtGui

try:
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


DEFAULT_SYSTEM_CONFIG: Dict[str, Any] = {
    "target_ip": "192.168.1.170",
    "target_port": 9000,
    "protocol": "TCP",
    "usb_port": "COM3",
    "baudrate": 115200,
    "theme": "Dark Mode",
    "record_path": "./data_logs",
    "record_filename": "saguling_mission",
    "sd_filename": "data_backup.csv",
    "download_path": "./downloads",
    "joystick_enabled": True,
    "joystick_deadzone": 0.15,
    "joystick_max_speed": 400,
    "water_quality_limits": {
        "ph": {
            "min": 6.0,
            "max": 9.0,
            "optimal_min": 6.5,
            "optimal_max": 8.5
        },
        "do": {
            "min": 4.0,
            "critical_min": 2.0,
            "optimal": 6.0
        },
        "temperature": {
            "min": 20.0,
            "max": 32.0
        },
        "conductivity": {
            "min": 50.0,
            "max": 1000.0
        }
    },
    "battery_limits": {
        "v_max": 25.2,
        "v_min": 19.8,
        "soc_warning": 30.0,
        "soc_critical": 20.0
    },
    "lmpc_defaults": {
        "np": 10,
        "nc": 3,
        "q_z": 100.0,
        "q_yaw": 50.0,
        "r_thrust": 0.1,
        "max_thrust_pwm_delta": 300
    },
    "ea_dsra_defaults": {
        "temp": {
            "e": 0.2,
            "s": 200,
            "tmin": 1.0,
            "tmax": 30.0
        },
        "do": {
            "e": 0.15,
            "s": 150,
            "tmin": 1.0,
            "tmax": 60.0
        },
        "ph": {
            "e": 0.05,
            "s": 300,
            "tmin": 1.0,
            "tmax": 60.0
        },
        "cond": {
            "e": 5.0,
            "s": 100,
            "tmin": 1.0,
            "tmax": 45.0
        },
        "soc_threshold": 30.0
    }
}


class ConfigSettingsTab(QtWidgets.QWidget):
    """
    Dedicated GCS Parameter Management & JSON Configuration Editor Tab.
    Provides an intuitive, human-centered parameter tuning interface.
    """
    config_applied = QtCore.pyqtSignal(dict)
    command_generated = QtCore.pyqtSignal(str)
    theme_changed = QtCore.pyqtSignal(str)
    log_emitted = QtCore.pyqtSignal(str)

    def __init__(self, config_path: str = "./config/gui_config.json", current_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.config_path = os.path.abspath(config_path)
        self.active_config = copy.deepcopy(current_config) if current_config else copy.deepcopy(DEFAULT_SYSTEM_CONFIG)
        self._block_sync = False

        self.init_ui()
        self.load_dict_to_form(self.active_config)

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # =========================================================
        # 1. TOP TOOLBAR / ACTION BAR
        # =========================================================
        top_bar = QtWidgets.QFrame()
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #1A1D23;
                border: 1px solid #2D3139;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        tb_layout = QtWidgets.QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(10)

        # Title & Active file label
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QtWidgets.QLabel("Pengaturan Parameter Sistem")
        lbl_title.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 13px; letter-spacing: 0.5px;")
        
        self.lbl_file_status = QtWidgets.QLabel(f"File Aktif: {self.config_path}")
        self.lbl_file_status.setStyleSheet("color: #00E5FF; font-size: 10px; font-family: 'Consolas', monospace;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(self.lbl_file_status)
        tb_layout.addLayout(title_box)

        tb_layout.addStretch()

        # Action Buttons
        self.btn_load_json = QtWidgets.QPushButton("Buka File JSON...")
        self.btn_load_json.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_load_json.setToolTip("Buka dan muat konfigurasi dari berkas JSON eksternal")
        self.btn_load_json.clicked.connect(self.on_load_json_dialog)
        tb_layout.addWidget(self.btn_load_json)

        self.btn_save_as = QtWidgets.QPushButton("Simpan Profil Sebagai...")
        self.btn_save_as.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_save_as.setToolTip("Ekspor parameter aktif ke berkas .json baru")
        self.btn_save_as.clicked.connect(self.on_save_as_dialog)
        tb_layout.addWidget(self.btn_save_as)

        self.btn_reset_def = QtWidgets.QPushButton("Reset Default")
        self.btn_reset_def.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_reset_def.setToolTip("Kembalikan seluruh parameter ke nilai standar awal")
        self.btn_reset_def.clicked.connect(self.on_reset_to_default)
        tb_layout.addWidget(self.btn_reset_def)

        self.btn_save_main = QtWidgets.QPushButton("Simpan Konfigurasi")
        self.btn_save_main.setObjectName("btnPrimary")
        self.btn_save_main.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_save_main.setStyleSheet("""
            QPushButton#btnPrimary {
                background-color: #1976D2;
                border: 1px solid #0D47A1;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton#btnPrimary:hover {
                background-color: #2196F3;
            }
        """)
        self.btn_save_main.setToolTip("Simpan parameter aktif langsung ke berkas konfigurasi utama")
        self.btn_save_main.clicked.connect(self.on_save_main_clicked)
        tb_layout.addWidget(self.btn_save_main)

        self.btn_apply_flash = QtWidgets.QPushButton("Terapkan ke Wahana")
        self.btn_apply_flash.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_apply_flash.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                border: 1px solid #1B5E20;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.btn_apply_flash.setToolTip("Terapkan ke sistem GCS dan kirim instruksi parameter langsung ke robot AUV")
        self.btn_apply_flash.clicked.connect(self.on_apply_and_flash_clicked)
        tb_layout.addWidget(self.btn_apply_flash)

        main_layout.addWidget(top_bar)

        # =========================================================
        # 2. MAIN BODY (SPLIT VIEW: FORM SECTIONS + LIVE JSON)
        # =========================================================
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # --- LEFT PANEL: PARAMETER FORM (SCROLLABLE) ---
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        form_container = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 8, 0)
        form_layout.setSpacing(10)

        # Card 1: Komunikasi & Jaringan
        form_layout.addWidget(self._build_card_network())

        # Card 2: LMPC Controller Parameters
        form_layout.addWidget(self._build_card_lmpc())

        # Card 3: EA-DSRA Adaptive Sampling
        form_layout.addWidget(self._build_card_ea_dsra())

        # Card 4: Ambang Batas Sensor & Keamanan
        form_layout.addWidget(self._build_card_safety())

        # Card 5: Joystick & Konfigurasi Penyimpanan
        form_layout.addWidget(self._build_card_storage_joystick())

        form_layout.addStretch()
        scroll_area.setWidget(form_container)
        splitter.addWidget(scroll_area)

        # --- RIGHT PANEL: LIVE JSON INSPECTOR ---
        json_panel = QtWidgets.QFrame()
        json_panel.setStyleSheet("""
            QFrame {
                background-color: #14161A;
                border: 1px solid #2B2F38;
                border-radius: 6px;
            }
        """)
        jp_layout = QtWidgets.QVBoxLayout(json_panel)
        jp_layout.setContentsMargins(10, 8, 10, 8)
        jp_layout.setSpacing(6)

        jp_header = QtWidgets.QHBoxLayout()
        lbl_json_title = QtWidgets.QLabel("Pratinjau JSON Langsung")
        lbl_json_title.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 11px;")
        jp_header.addWidget(lbl_json_title)

        jp_header.addStretch()

        self.lbl_sync_badge = QtWidgets.QLabel("[Tersinkronisasi]")
        self.lbl_sync_badge.setStyleSheet("color: #00E676; font-size: 10px; font-weight: bold;")
        jp_header.addWidget(self.lbl_sync_badge)
        jp_layout.addLayout(jp_header)

        self.txt_json_editor = QtWidgets.QPlainTextEdit()
        self.txt_json_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0D0F12;
                border: 1px solid #242830;
                border-radius: 4px;
                color: #A9B7C6;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                selection-background-color: #214283;
            }
        """)
        self.txt_json_editor.textChanged.connect(self._on_json_editor_text_changed)
        jp_layout.addWidget(self.txt_json_editor)

        # JSON Utility Buttons
        jp_btns = QtWidgets.QHBoxLayout()
        self.btn_copy_json = QtWidgets.QPushButton("Salin JSON")
        self.btn_copy_json.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_copy_json.clicked.connect(self.on_copy_json_to_clipboard)
        jp_btns.addWidget(self.btn_copy_json)

        self.btn_apply_raw_json = QtWidgets.QPushButton("Terapkan Teks JSON ke Form")
        self.btn_apply_raw_json.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_apply_raw_json.setToolTip("Muat teks JSON editor di atas langsung ke formulir pengaturan")
        self.btn_apply_raw_json.clicked.connect(self.on_apply_raw_json_to_form)
        jp_btns.addWidget(self.btn_apply_raw_json)

        jp_layout.addLayout(jp_btns)
        splitter.addWidget(json_panel)

        # Set ratio: 60% Form, 40% Live JSON
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter, stretch=1)

    # =========================================================
    # --- FORM CARDS BUILDERS ---
    # =========================================================
    def _build_card_network(self) -> QtWidgets.QGroupBox:
        grp = QtWidgets.QGroupBox("Koneksi Jaringan & Serial Telemetri")
        layout = QtWidgets.QGridLayout(grp)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(6)

        # Row 0: Target IP & Port
        layout.addWidget(QtWidgets.QLabel("Alamat IP Wahana:"), 0, 0)
        self.txt_target_ip = QtWidgets.QLineEdit("192.168.1.170")
        self.txt_target_ip.textChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.txt_target_ip, 0, 1)

        layout.addWidget(QtWidgets.QLabel("Port Komunikasi:"), 0, 2)
        self.sp_target_port = QtWidgets.QSpinBox()
        self.sp_target_port.setRange(1024, 65535)
        self.sp_target_port.setValue(9000)
        self.sp_target_port.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_target_port, 0, 3)

        # Row 1: Protokol & Serial Port
        layout.addWidget(QtWidgets.QLabel("Protokol Jaringan:"), 1, 0)
        self.cb_protocol = QtWidgets.QComboBox()
        self.cb_protocol.addItems(["TCP", "UDP"])
        self.cb_protocol.currentTextChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.cb_protocol, 1, 1)

        layout.addWidget(QtWidgets.QLabel("Port Serial (USB/COM):"), 1, 2)
        com_box = QtWidgets.QHBoxLayout()
        self.cb_usb_port = QtWidgets.QComboBox()
        self.cb_usb_port.setEditable(True)
        self.refresh_serial_ports()
        self.cb_usb_port.currentTextChanged.connect(self._sync_form_to_json)
        com_box.addWidget(self.cb_usb_port, stretch=3)

        btn_refresh_ports = QtWidgets.QPushButton("Pindai")
        btn_refresh_ports.setFixedWidth(52)
        btn_refresh_ports.setCursor(QtCore.Qt.PointingHandCursor)
        btn_refresh_ports.setToolTip("Pindai ulang port serial COM yang terhubung ke PC")
        btn_refresh_ports.clicked.connect(self.refresh_serial_ports)
        com_box.addWidget(btn_refresh_ports)
        layout.addLayout(com_box, 1, 3)

        # Row 2: Baudrate
        layout.addWidget(QtWidgets.QLabel("Baudrate Serial (bps):"), 2, 0)
        self.cb_baudrate = QtWidgets.QComboBox()
        for b in ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]:
            self.cb_baudrate.addItem(b)
        self.cb_baudrate.setCurrentText("115200")
        self.cb_baudrate.currentTextChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.cb_baudrate, 2, 1)

        return grp

    def _build_card_lmpc(self) -> QtWidgets.QGroupBox:
        grp = QtWidgets.QGroupBox("Kontroler Gerak & Kedalaman (LMPC)")
        layout = QtWidgets.QGridLayout(grp)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(6)

        # Row 0: Np & Nc
        layout.addWidget(QtWidgets.QLabel("Prediction Horizon (Np):"), 0, 0)
        self.sp_lmpc_np = QtWidgets.QSpinBox()
        self.sp_lmpc_np.setRange(2, 50)
        self.sp_lmpc_np.setValue(10)
        self.sp_lmpc_np.setToolTip("Jumlah langkah prediksi masa depan yang dihitung LMPC")
        self.sp_lmpc_np.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_lmpc_np, 0, 1)

        layout.addWidget(QtWidgets.QLabel("Control Horizon (Nc):"), 0, 2)
        self.sp_lmpc_nc = QtWidgets.QSpinBox()
        self.sp_lmpc_nc.setRange(1, 20)
        self.sp_lmpc_nc.setValue(3)
        self.sp_lmpc_nc.setToolTip("Jumlah langkah kendali yang dioptimasi oleh solver MPC")
        self.sp_lmpc_nc.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_lmpc_nc, 0, 3)

        # Row 1: Qz & Qyaw
        layout.addWidget(QtWidgets.QLabel("Bobot Kedalaman (Q_z):"), 1, 0)
        self.sp_lmpc_qz = QtWidgets.QDoubleSpinBox()
        self.sp_lmpc_qz.setRange(0.1, 5000.0)
        self.sp_lmpc_qz.setValue(100.0)
        self.sp_lmpc_qz.setToolTip("Bobot penalti error kedalaman (semakin besar semakin agresif)")
        self.sp_lmpc_qz.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_lmpc_qz, 1, 1)

        layout.addWidget(QtWidgets.QLabel("Bobot Heading/Yaw (Q_yaw):"), 1, 2)
        self.sp_lmpc_qyaw = QtWidgets.QDoubleSpinBox()
        self.sp_lmpc_qyaw.setRange(0.1, 5000.0)
        self.sp_lmpc_qyaw.setValue(50.0)
        self.sp_lmpc_qyaw.setToolTip("Bobot penalti error sudut hadap arah wahana")
        self.sp_lmpc_qyaw.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_lmpc_qyaw, 1, 3)

        # Row 2: R & Max PWM Delta
        layout.addWidget(QtWidgets.QLabel("Bobot Input Laju (R_thrust):"), 2, 0)
        self.sp_lmpc_r = QtWidgets.QDoubleSpinBox()
        self.sp_lmpc_r.setRange(0.001, 10.0)
        self.sp_lmpc_r.setDecimals(3)
        self.sp_lmpc_r.setValue(0.100)
        self.sp_lmpc_r.setToolTip("Penalti laju perubahan tenaga thruster (semakin besar semakin halus dan hemat)")
        self.sp_lmpc_r.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_lmpc_r, 2, 1)

        layout.addWidget(QtWidgets.QLabel("Batas Laju Pendorong (Max ΔPWM):"), 2, 2)
        self.sp_lmpc_max_pwm = QtWidgets.QSpinBox()
        self.sp_lmpc_max_pwm.setRange(50, 500)
        self.sp_lmpc_max_pwm.setValue(300)
        self.sp_lmpc_max_pwm.setToolTip("Batas perubahan daya maksimum per siklus kontrol")
        self.sp_lmpc_max_pwm.valueChanged.connect(self._sync_form_to_json)
        layout.addWidget(self.sp_lmpc_max_pwm, 2, 3)

        # Row 3: Quick Flash LMPC button
        btn_flash_lmpc = QtWidgets.QPushButton("Kirim Parameter LMPC ke Wahana")
        btn_flash_lmpc.setCursor(QtCore.Qt.PointingHandCursor)
        btn_flash_lmpc.setStyleSheet("background-color: #263238; border: 1px solid #37474F; color: #80CBC4; font-weight: bold; padding: 5px;")
        btn_flash_lmpc.clicked.connect(self.flash_lmpc_only)
        layout.addWidget(btn_flash_lmpc, 3, 0, 1, 4)

        return grp

    def _build_card_ea_dsra(self) -> QtWidgets.QGroupBox:
        grp = QtWidgets.QGroupBox("Sampling Dinamis Sensor & Daya (EA-DSRA)")
        v_layout = QtWidgets.QVBoxLayout(grp)
        v_layout.setContentsMargins(10, 12, 10, 10)
        v_layout.setSpacing(8)

        # Top line: Critical SoC threshold
        soc_row = QtWidgets.QHBoxLayout()
        soc_row.addWidget(QtWidgets.QLabel("Batas Baterai Lemah untuk Mode Hemat (SoC %):"))
        self.sp_dsra_soc_thresh = QtWidgets.QDoubleSpinBox()
        self.sp_dsra_soc_thresh.setRange(5.0, 99.0)
        self.sp_dsra_soc_thresh.setValue(30.0)
        self.sp_dsra_soc_thresh.setToolTip("Batas kapasitas baterai di mana algoritma mengutamakan penghematan daya (Bisa dinaikkan hingga 99% untuk uji respon)")
        self.sp_dsra_soc_thresh.valueChanged.connect(self._sync_form_to_json)
        soc_row.addWidget(self.sp_dsra_soc_thresh)
        soc_row.addStretch()
        v_layout.addLayout(soc_row)

        # Grid Table for 4 Sensors: Temperature, DO, pH, Conductivity
        tbl_grid = QtWidgets.QGridLayout()
        tbl_grid.setHorizontalSpacing(8)
        tbl_grid.setVerticalSpacing(4)

        headers = ["Sensor Kualitas Air", "Toleransi Deviasi (e)", "Sensitivitas (S)", "Interval Cepat / Min (s)", "Interval Lambat / Max (s)"]
        for col, h in enumerate(headers):
            lbl = QtWidgets.QLabel(h)
            lbl.setStyleSheet("color: #B0BEC5; font-weight: bold; font-size: 10px;")
            tbl_grid.addWidget(lbl, 0, col)

        self.dsra_inputs: Dict[str, Dict[str, QtWidgets.QWidget]] = {}
        sensors = [
            ("temp", "Suhu Air (°C)"),
            ("do", "Oksigen Terlarut / DO (mg/L)"),
            ("ph", "Derajat Keasaman / pH"),
            ("cond", "Konduktivitas Air (µS/cm)")
        ]

        for r_idx, (s_key, s_name) in enumerate(sensors, start=1):
            lbl_name = QtWidgets.QLabel(s_name)
            tbl_grid.addWidget(lbl_name, r_idx, 0)

            # e (DoubleSpinBox)
            sp_e = QtWidgets.QDoubleSpinBox()
            sp_e.setRange(0.001, 50.0)
            sp_e.setDecimals(3)
            sp_e.setValue(0.1)
            sp_e.setToolTip("Ambang batas perubahan data sebelum sampling dipercepat")
            sp_e.valueChanged.connect(self._sync_form_to_json)
            tbl_grid.addWidget(sp_e, r_idx, 1)

            # S (SpinBox)
            sp_s = QtWidgets.QSpinBox()
            sp_s.setRange(10, 1000)
            sp_s.setValue(200)
            sp_s.setToolTip("Faktor pengali sensitivitas sampling")
            sp_s.valueChanged.connect(self._sync_form_to_json)
            tbl_grid.addWidget(sp_s, r_idx, 2)

            # Tmin (DoubleSpinBox)
            sp_tmin = QtWidgets.QDoubleSpinBox()
            sp_tmin.setRange(0.2, 60.0)
            sp_tmin.setValue(1.0)
            sp_tmin.setToolTip("Periode sampling tercepat saat terjadi fluktuasi air tajam")
            sp_tmin.valueChanged.connect(self._sync_form_to_json)
            tbl_grid.addWidget(sp_tmin, r_idx, 3)

            # Tmax (DoubleSpinBox)
            sp_tmax = QtWidgets.QDoubleSpinBox()
            sp_tmax.setRange(1.0, 300.0)
            sp_tmax.setValue(60.0)
            sp_tmax.setToolTip("Periode sampling terpanjang saat air stabil / hemat daya")
            sp_tmax.valueChanged.connect(self._sync_form_to_json)
            tbl_grid.addWidget(sp_tmax, r_idx, 4)

            self.dsra_inputs[s_key] = {
                "e": sp_e,
                "s": sp_s,
                "tmin": sp_tmin,
                "tmax": sp_tmax
            }

        v_layout.addLayout(tbl_grid)

        # Quick Flash EA-DSRA button
        btn_flash_dsra = QtWidgets.QPushButton("Kirim Parameter EA-DSRA ke Wahana")
        btn_flash_dsra.setCursor(QtCore.Qt.PointingHandCursor)
        btn_flash_dsra.setStyleSheet("background-color: #263238; border: 1px solid #37474F; color: #80CBC4; font-weight: bold; padding: 5px;")
        btn_flash_dsra.clicked.connect(self.flash_dsra_only)
        v_layout.addWidget(btn_flash_dsra)

        return grp

    def _build_card_safety(self) -> QtWidgets.QGroupBox:
        grp = QtWidgets.QGroupBox("Ambang Batas Sensor & Keamanan (Baku Mutu PP 22/2021)")
        grid = QtWidgets.QGridLayout(grp)
        grid.setContentsMargins(10, 12, 10, 10)
        grid.setSpacing(6)

        # pH Limits
        grid.addWidget(QtWidgets.QLabel("pH Baku Mutu (Min - Max):"), 0, 0)
        ph_box = QtWidgets.QHBoxLayout()
        self.sp_ph_min = QtWidgets.QDoubleSpinBox()
        self.sp_ph_min.setRange(0.0, 14.0)
        self.sp_ph_min.setValue(6.0)
        self.sp_ph_min.valueChanged.connect(self._sync_form_to_json)
        ph_box.addWidget(self.sp_ph_min)

        self.sp_ph_max = QtWidgets.QDoubleSpinBox()
        self.sp_ph_max.setRange(0.0, 14.0)
        self.sp_ph_max.setValue(9.0)
        self.sp_ph_max.valueChanged.connect(self._sync_form_to_json)
        ph_box.addWidget(self.sp_ph_max)
        grid.addLayout(ph_box, 0, 1)

        # DO Limits
        grid.addWidget(QtWidgets.QLabel("DO Baku Mutu - Kritis (mg/L):"), 0, 2)
        do_box = QtWidgets.QHBoxLayout()
        self.sp_do_min = QtWidgets.QDoubleSpinBox()
        self.sp_do_min.setRange(0.0, 20.0)
        self.sp_do_min.setValue(4.0)
        self.sp_do_min.valueChanged.connect(self._sync_form_to_json)
        do_box.addWidget(self.sp_do_min)

        self.sp_do_crit = QtWidgets.QDoubleSpinBox()
        self.sp_do_crit.setRange(0.0, 20.0)
        self.sp_do_crit.setValue(2.0)
        self.sp_do_crit.valueChanged.connect(self._sync_form_to_json)
        do_box.addWidget(self.sp_do_crit)
        grid.addLayout(do_box, 0, 3)

        # Temperature Limits
        grid.addWidget(QtWidgets.QLabel("Suhu Air Min - Max (°C):"), 1, 0)
        temp_box = QtWidgets.QHBoxLayout()
        self.sp_temp_min = QtWidgets.QDoubleSpinBox()
        self.sp_temp_min.setRange(0.0, 50.0)
        self.sp_temp_min.setValue(20.0)
        self.sp_temp_min.valueChanged.connect(self._sync_form_to_json)
        temp_box.addWidget(self.sp_temp_min)

        self.sp_temp_max = QtWidgets.QDoubleSpinBox()
        self.sp_temp_max.setRange(0.0, 50.0)
        self.sp_temp_max.setValue(32.0)
        self.sp_temp_max.valueChanged.connect(self._sync_form_to_json)
        temp_box.addWidget(self.sp_temp_max)
        grid.addLayout(temp_box, 1, 1)

        # Conductivity Limits
        grid.addWidget(QtWidgets.QLabel("Konduktivitas Min - Max (µS/cm):"), 1, 2)
        cond_box = QtWidgets.QHBoxLayout()
        self.sp_cond_min = QtWidgets.QDoubleSpinBox()
        self.sp_cond_min.setRange(0.0, 10000.0)
        self.sp_cond_min.setValue(50.0)
        self.sp_cond_min.valueChanged.connect(self._sync_form_to_json)
        cond_box.addWidget(self.sp_cond_min)

        self.sp_cond_max = QtWidgets.QDoubleSpinBox()
        self.sp_cond_max.setRange(0.0, 10000.0)
        self.sp_cond_max.setValue(1000.0)
        self.sp_cond_max.valueChanged.connect(self._sync_form_to_json)
        cond_box.addWidget(self.sp_cond_max)
        grid.addLayout(cond_box, 1, 3)

        # Battery Limits (Vmax, Vmin, SoC warn, SoC crit)
        grid.addWidget(QtWidgets.QLabel("Tegangan Baterai Vmax - Vmin (V):"), 2, 0)
        v_box = QtWidgets.QHBoxLayout()
        self.sp_v_max = QtWidgets.QDoubleSpinBox()
        self.sp_v_max.setRange(10.0, 40.0)
        self.sp_v_max.setValue(25.2)
        self.sp_v_max.valueChanged.connect(self._sync_form_to_json)
        v_box.addWidget(self.sp_v_max)

        self.sp_v_min = QtWidgets.QDoubleSpinBox()
        self.sp_v_min.setRange(10.0, 40.0)
        self.sp_v_min.setValue(19.8)
        self.sp_v_min.valueChanged.connect(self._sync_form_to_json)
        v_box.addWidget(self.sp_v_min)
        grid.addLayout(v_box, 2, 1)

        grid.addWidget(QtWidgets.QLabel("Alarm Baterai SoC Peringatan - Kritis (%):"), 2, 2)
        soc_box = QtWidgets.QHBoxLayout()
        self.sp_soc_warn = QtWidgets.QDoubleSpinBox()
        self.sp_soc_warn.setRange(5.0, 60.0)
        self.sp_soc_warn.setValue(30.0)
        self.sp_soc_warn.valueChanged.connect(self._sync_form_to_json)
        soc_box.addWidget(self.sp_soc_warn)

        self.sp_soc_crit = QtWidgets.QDoubleSpinBox()
        self.sp_soc_crit.setRange(5.0, 40.0)
        self.sp_soc_crit.setValue(20.0)
        self.sp_soc_crit.valueChanged.connect(self._sync_form_to_json)
        soc_box.addWidget(self.sp_soc_crit)
        grid.addLayout(soc_box, 2, 3)

        return grp

    def _build_card_storage_joystick(self) -> QtWidgets.QGroupBox:
        grp = QtWidgets.QGroupBox("Pengaturan Stik Gamepad, Log & Tampilan")
        grid = QtWidgets.QGridLayout(grp)
        grid.setContentsMargins(10, 12, 10, 10)
        grid.setSpacing(6)

        # Joystick Enable & Deadzone
        self.cb_joy_enable = QtWidgets.QCheckBox("Aktifkan USB Joystick / Gamepad")
        self.cb_joy_enable.setChecked(True)
        self.cb_joy_enable.toggled.connect(self._sync_form_to_json)
        grid.addWidget(self.cb_joy_enable, 0, 0)

        joy_param = QtWidgets.QHBoxLayout()
        joy_param.addWidget(QtWidgets.QLabel("Deadzone:"))
        self.sp_joy_deadzone = QtWidgets.QDoubleSpinBox()
        self.sp_joy_deadzone.setRange(0.01, 0.50)
        self.sp_joy_deadzone.setSingleStep(0.05)
        self.sp_joy_deadzone.setValue(0.15)
        self.sp_joy_deadzone.setToolTip("Toleransi posisi tengah joystick untuk mencegah pergerakan tak sengaja")
        self.sp_joy_deadzone.valueChanged.connect(self._sync_form_to_json)
        joy_param.addWidget(self.sp_joy_deadzone)

        joy_param.addWidget(QtWidgets.QLabel("Max Speed (PWM Delta):"))
        self.sp_joy_speed = QtWidgets.QSpinBox()
        self.sp_joy_speed.setRange(50, 450)
        self.sp_joy_speed.setValue(400)
        self.sp_joy_speed.setToolTip("Batas maksimum daya dorong saat menggunakan stik joystick")
        self.sp_joy_speed.valueChanged.connect(self._sync_form_to_json)
        joy_param.addWidget(self.sp_joy_speed)
        grid.addLayout(joy_param, 0, 1, 1, 3)

        # Storage paths
        grid.addWidget(QtWidgets.QLabel("Folder Rekaman CSV Telemetri:"), 1, 0)
        rec_box = QtWidgets.QHBoxLayout()
        self.txt_record_path = QtWidgets.QLineEdit("./data_logs")
        self.txt_record_path.textChanged.connect(self._sync_form_to_json)
        rec_box.addWidget(self.txt_record_path)

        btn_browse_rec = QtWidgets.QPushButton("Pilih Folder...")
        btn_browse_rec.setCursor(QtCore.Qt.PointingHandCursor)
        btn_browse_rec.clicked.connect(self.on_browse_record_path)
        rec_box.addWidget(btn_browse_rec)
        grid.addLayout(rec_box, 1, 1, 1, 3)

        grid.addWidget(QtWidgets.QLabel("Awalan Nama Berkas Misi:"), 2, 0)
        self.txt_rec_filename = QtWidgets.QLineEdit("saguling_mission")
        self.txt_rec_filename.textChanged.connect(self._sync_form_to_json)
        grid.addWidget(self.txt_rec_filename, 2, 1)

        grid.addWidget(QtWidgets.QLabel("Tema Tampilan Antarmuka:"), 2, 2)
        self.cb_theme = QtWidgets.QComboBox()
        self.cb_theme.addItems(["Dark Mode", "Light Mode"])
        self.cb_theme.currentTextChanged.connect(self._on_theme_selection_changed)
        grid.addWidget(self.cb_theme, 2, 3)

        return grp

    # =========================================================
    # --- SYNCHRONIZATION & DATA BINDING ---
    # =========================================================
    def refresh_serial_ports(self):
        curr = self.cb_usb_port.currentText() if hasattr(self, "cb_usb_port") else ""
        self.cb_usb_port.clear()
        found = []
        if HAS_SERIAL:
            try:
                for port in serial.tools.list_ports.comports():
                    found.append(port.device)
            except Exception:
                pass
        
        if not found:
            found = ["COM1", "COM2", "COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyACM0"]
        
        self.cb_usb_port.addItems(found)
        if curr and curr in found:
            self.cb_usb_port.setCurrentText(curr)
        elif "COM3" in found:
            self.cb_usb_port.setCurrentText("COM3")

    def _sync_form_to_json(self):
        if self._block_sync:
            return
        cfg = self.collect_form_to_dict()
        formatted = json.dumps(cfg, indent=4)
        self._block_sync = True
        self.txt_json_editor.setPlainText(formatted)
        self._block_sync = False
        self.lbl_sync_badge.setText("[Tersinkronisasi]")
        self.lbl_sync_badge.setStyleSheet("color: #00E676; font-size: 10px; font-weight: bold;")

    def _on_json_editor_text_changed(self):
        if self._block_sync:
            return
        # Indicate that editor text has manual edits not yet validated into form
        self.lbl_sync_badge.setText("[Diedit Manual - Belum Diterapkan]")
        self.lbl_sync_badge.setStyleSheet("color: #FFA726; font-size: 10px; font-weight: bold;")

    def on_apply_raw_json_to_form(self):
        raw_text = self.txt_json_editor.toPlainText().strip()
        try:
            parsed = json.loads(raw_text)
            self.load_dict_to_form(parsed)
            self.lbl_sync_badge.setText("[Tersinkronisasi]")
            self.lbl_sync_badge.setStyleSheet("color: #00E676; font-size: 10px; font-weight: bold;")
            QtWidgets.QMessageBox.information(self, "Berhasil", "Teks JSON berhasil dimuat ke dalam formulir parameter!")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Sintaks JSON Salah", f"Format JSON tidak valid:\n{e}")

    def on_copy_json_to_clipboard(self):
        text = self.txt_json_editor.toPlainText()
        QtWidgets.QApplication.clipboard().setText(text)
        self.log_emitted.emit("[CONFIG] Salinan JSON berhasil disalin ke clipboard.")

    def on_browse_record_path(self):
        curr_dir = self.txt_record_path.text().strip()
        selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Pilih Folder Rekaman Telemetri", curr_dir or ".")
        if selected:
            self.txt_record_path.setText(selected)

    def _on_theme_selection_changed(self, new_theme: str):
        self._sync_form_to_json()
        self.theme_changed.emit(new_theme)

    # =========================================================
    # --- LOAD & COLLECT DICTIONARY ---
    # =========================================================
    def load_dict_to_form(self, cfg: Dict[str, Any]):
        self._block_sync = True
        try:
            # Network
            self.txt_target_ip.setText(str(cfg.get("target_ip", "192.168.1.170")))
            self.sp_target_port.setValue(int(cfg.get("target_port", 9000)))
            self.cb_protocol.setCurrentText(str(cfg.get("protocol", "TCP")).upper())
            self.cb_usb_port.setCurrentText(str(cfg.get("usb_port", "COM3")))
            self.cb_baudrate.setCurrentText(str(cfg.get("baudrate", 115200)))

            # LMPC
            lmpc = cfg.get("lmpc_defaults", {})
            self.sp_lmpc_np.setValue(int(lmpc.get("np", 10)))
            self.sp_lmpc_nc.setValue(int(lmpc.get("nc", 3)))
            self.sp_lmpc_qz.setValue(float(lmpc.get("q_z", 100.0)))
            self.sp_lmpc_qyaw.setValue(float(lmpc.get("q_yaw", 50.0)))
            self.sp_lmpc_r.setValue(float(lmpc.get("r_thrust", 0.1)))
            self.sp_lmpc_max_pwm.setValue(int(lmpc.get("max_thrust_pwm_delta", 300)))

            # EA-DSRA
            dsra = cfg.get("ea_dsra_defaults", {})
            self.sp_dsra_soc_thresh.setValue(float(dsra.get("soc_threshold", 30.0)))
            for s_key, inputs in self.dsra_inputs.items():
                s_dict = dsra.get(s_key, {})
                inputs["e"].setValue(float(s_dict.get("e", 0.1)))
                inputs["s"].setValue(int(s_dict.get("s", 200)))
                inputs["tmin"].setValue(float(s_dict.get("tmin", 1.0)))
                inputs["tmax"].setValue(float(s_dict.get("tmax", 30.0)))

            # Safety Limits
            wq = cfg.get("water_quality_limits", {})
            ph_lim = wq.get("ph", {})
            self.sp_ph_min.setValue(float(ph_lim.get("min", 6.0)))
            self.sp_ph_max.setValue(float(ph_lim.get("max", 9.0)))

            do_lim = wq.get("do", {})
            self.sp_do_min.setValue(float(do_lim.get("min", 4.0)))
            self.sp_do_crit.setValue(float(do_lim.get("critical_min", 2.0)))

            t_lim = wq.get("temperature", {})
            self.sp_temp_min.setValue(float(t_lim.get("min", 20.0)))
            self.sp_temp_max.setValue(float(t_lim.get("max", 32.0)))

            c_lim = wq.get("conductivity", {})
            self.sp_cond_min.setValue(float(c_lim.get("min", 50.0)))
            self.sp_cond_max.setValue(float(c_lim.get("max", 1000.0)))

            # Battery Limits
            b_lim = cfg.get("battery_limits", {})
            self.sp_v_max.setValue(float(b_lim.get("v_max", 25.2)))
            self.sp_v_min.setValue(float(b_lim.get("v_min", 19.8)))
            self.sp_soc_warn.setValue(float(b_lim.get("soc_warning", 30.0)))
            self.sp_soc_crit.setValue(float(b_lim.get("soc_critical", 20.0)))

            # Joystick & Storage
            self.cb_joy_enable.setChecked(bool(cfg.get("joystick_enabled", True)))
            self.sp_joy_deadzone.setValue(float(cfg.get("joystick_deadzone", 0.15)))
            self.sp_joy_speed.setValue(int(cfg.get("joystick_max_speed", 400)))
            self.txt_record_path.setText(str(cfg.get("record_path", "./data_logs")))
            self.txt_rec_filename.setText(str(cfg.get("record_filename", "saguling_mission")))
            self.cb_theme.setCurrentText(str(cfg.get("theme", "Dark Mode")))

        finally:
            self._block_sync = False

        formatted = json.dumps(cfg, indent=4)
        self._block_sync = True
        self.txt_json_editor.setPlainText(formatted)
        self._block_sync = False
        self.lbl_sync_badge.setText("[Tersinkronisasi]")
        self.lbl_sync_badge.setStyleSheet("color: #00E676; font-size: 10px; font-weight: bold;")

    def collect_form_to_dict(self) -> Dict[str, Any]:
        cfg = copy.deepcopy(DEFAULT_SYSTEM_CONFIG)

        # Network
        cfg["target_ip"] = self.txt_target_ip.text().strip()
        cfg["target_port"] = self.sp_target_port.value()
        cfg["protocol"] = self.cb_protocol.currentText()
        cfg["usb_port"] = self.cb_usb_port.currentText().strip()
        try:
            cfg["baudrate"] = int(self.cb_baudrate.currentText())
        except ValueError:
            cfg["baudrate"] = 115200

        # LMPC
        cfg["lmpc_defaults"] = {
            "np": self.sp_lmpc_np.value(),
            "nc": self.sp_lmpc_nc.value(),
            "q_z": self.sp_lmpc_qz.value(),
            "q_yaw": self.sp_lmpc_qyaw.value(),
            "r_thrust": self.sp_lmpc_r.value(),
            "max_thrust_pwm_delta": self.sp_lmpc_max_pwm.value()
        }

        # EA-DSRA
        ea_dict = {"soc_threshold": self.sp_dsra_soc_thresh.value()}
        for s_key, inputs in self.dsra_inputs.items():
            ea_dict[s_key] = {
                "e": inputs["e"].value(),
                "s": inputs["s"].value(),
                "tmin": inputs["tmin"].value(),
                "tmax": inputs["tmax"].value()
            }
        cfg["ea_dsra_defaults"] = ea_dict

        # Water quality limits
        cfg["water_quality_limits"] = {
            "ph": {
                "min": self.sp_ph_min.value(),
                "max": self.sp_ph_max.value(),
                "optimal_min": 6.5,
                "optimal_max": 8.5
            },
            "do": {
                "min": self.sp_do_min.value(),
                "critical_min": self.sp_do_crit.value(),
                "optimal": 6.0
            },
            "temperature": {
                "min": self.sp_temp_min.value(),
                "max": self.sp_temp_max.value()
            },
            "conductivity": {
                "min": self.sp_cond_min.value(),
                "max": self.sp_cond_max.value()
            }
        }

        # Battery limits
        cfg["battery_limits"] = {
            "v_max": self.sp_v_max.value(),
            "v_min": self.sp_v_min.value(),
            "soc_warning": self.sp_soc_warn.value(),
            "soc_critical": self.sp_soc_crit.value()
        }

        # Joystick & storage
        cfg["joystick_enabled"] = self.cb_joy_enable.isChecked()
        cfg["joystick_deadzone"] = self.sp_joy_deadzone.value()
        cfg["joystick_max_speed"] = self.sp_joy_speed.value()
        cfg["record_path"] = self.txt_record_path.text().strip()
        cfg["record_filename"] = self.txt_rec_filename.text().strip()
        cfg["theme"] = self.cb_theme.currentText()

        return cfg

    # =========================================================
    # --- FILE ACTIONS & FLASH COMMANDS ---
    # =========================================================
    def on_load_json_dialog(self):
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Pilih Berkas Profil Konfigurasi JSON",
            os.path.dirname(self.config_path),
            "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.config_path = os.path.abspath(filepath)
                self.lbl_file_status.setText(f"File Aktif: {self.config_path}")
                self.load_dict_to_form(loaded)
                self.log_emitted.emit(f"[CONFIG] Profil dimuat dari: {filepath}")
                QtWidgets.QMessageBox.information(self, "Profil Dimuat", f"Konfigurasi dari:\n{filepath}\nberhasil dimuat ke editor.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Gagal Memuat JSON", f"Gagal membaca file JSON:\n{e}")

    def on_save_as_dialog(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Simpan Sebagai Profil JSON Baru",
            os.path.dirname(self.config_path),
            "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            if not filepath.endswith(".json"):
                filepath += ".json"
            cfg = self.collect_form_to_dict()
            try:
                os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4)
                self.config_path = os.path.abspath(filepath)
                self.lbl_file_status.setText(f"File Aktif: {self.config_path}")
                self.log_emitted.emit(f"[CONFIG] Profil berhasil diekspor ke: {filepath}")
                QtWidgets.QMessageBox.information(self, "Berhasil Disimpan", f"Profil konfigurasi berhasil disimpan ke:\n{filepath}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Gagal Menyimpan", f"Gagal menulis file JSON:\n{e}")

    def on_reset_to_default(self):
        reply = QtWidgets.QMessageBox.question(
            self, "Konfirmasi Reset",
            "Apakah Anda yakin ingin mengembalikan seluruh parameter ke pengaturan pabrik (default)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.load_dict_to_form(DEFAULT_SYSTEM_CONFIG)
            self.log_emitted.emit("[CONFIG] Parameter di-reset ke konfigurasi default.")

    def on_save_main_clicked(self):
        cfg = self.collect_form_to_dict()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            self.config_applied.emit(cfg)
            self.log_emitted.emit(f"[CONFIG] Disimpan ke file: {self.config_path}")
            QtWidgets.QMessageBox.information(
                self, "Konfigurasi Tersimpan",
                f"Konfigurasi berhasil disimpan ke berkas JSON:\n{self.config_path}\ndan diterapkan ke sistem GCS."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal Menyimpan", f"Gagal menyimpan ke {self.config_path}:\n{e}")

    def on_apply_and_flash_clicked(self):
        cfg = self.collect_form_to_dict()
        # 1. Save to JSON
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
        except Exception as e:
            self.log_emitted.emit(f"[CONFIG ERROR] Gagal simpan file: {e}")

        # 2. Emit config applied to GCS backend & UI
        self.config_applied.emit(cfg)

        # 3. Flash LMPC parameters
        np_v = cfg["lmpc_defaults"]["np"]
        nc_v = cfg["lmpc_defaults"]["nc"]
        qz_v = cfg["lmpc_defaults"]["q_z"]
        r_v = cfg["lmpc_defaults"]["r_thrust"]
        cmd_lmpc = f"LMPC_PARAM,{np_v},{nc_v},{qz_v:.2f},{r_v:.3f}\n"
        self.command_generated.emit(cmd_lmpc)

        # 4. Flash EA-DSRA parameters
        ea = cfg["ea_dsra_defaults"]
        soc_th = ea["soc_threshold"]
        for s_key, label in [("ph", "PH"), ("do", "DO"), ("temp", "TEMP"), ("cond", "COND")]:
            s_data = ea.get(s_key, {})
            cmd_dsra = f"EADSRA_PARAM,{label},{s_data.get('e', 0.1):.3f},{s_data.get('s', 200)},{soc_th:.1f}\n"
            self.command_generated.emit(cmd_dsra)

        # 5. Flash Speed limit
        spd = cfg["joystick_max_speed"]
        self.command_generated.emit(f"SPEED,{spd}\n")

        self.log_emitted.emit("[CONFIG] Seluruh parameter berhasil diterapkan dan dikirimkan ke wahana AUV.")
        QtWidgets.QMessageBox.information(
            self, "Terapkan & Kirim Selesai",
            "Konfigurasi berhasil disimpan ke JSON, diterapkan ke memori GCS, "
            "dan instruksi parameter (LMPC, EA-DSRA, Batas Kecepatan) telah dikirim ke robot!"
        )

    def flash_lmpc_only(self):
        np_v = self.sp_lmpc_np.value()
        nc_v = self.sp_lmpc_nc.value()
        qz_v = self.sp_lmpc_qz.value()
        r_v = self.sp_lmpc_r.value()
        cmd = f"LMPC_PARAM,{np_v},{nc_v},{qz_v:.2f},{r_v:.3f}\n"
        self.command_generated.emit(cmd)
        self.log_emitted.emit(f"[LMPC] Parameter terkirim: {cmd.strip()}")

    def flash_dsra_only(self):
        soc_th = self.sp_dsra_soc_thresh.value()
        for s_key, label in [("ph", "PH"), ("do", "DO"), ("temp", "TEMP"), ("cond", "COND")]:
            sp_dict = self.dsra_inputs[s_key]
            e_val = sp_dict["e"].value()
            s_val = sp_dict["s"].value()
            cmd = f"EADSRA_PARAM,{label},{e_val:.3f},{s_val},{soc_th:.1f}\n"
            self.command_generated.emit(cmd)
            self.log_emitted.emit(f"[EA-DSRA] Parameter terkirim: {cmd.strip()}")
