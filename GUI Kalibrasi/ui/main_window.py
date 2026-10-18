# -*- coding: utf-8 -*-
"""
Sensor Calibration Tool — Main Application
Replicates and enhances Program-WGG's exact layout, styling, and behavior.
Connects to Teensy 4.1 via Ethernet TCP to calibrate:
- Water Quality sensors: pH, EC, DO, Temperature
- Robot Motion & Orientation sensors: Gyroscope, Horizon Leveling, Magnetometer, Depth
- Real-time display, CSV recording with custom interval, and communication terminal log.
"""

import sys
import os
import csv
from datetime import datetime

from PyQt5 import QtWidgets, QtCore, QtGui
from core.comm_client import CommClient
from core.mock_server import MockCalibrationServer
from ui.styles import get_wgg_stylesheet
from ui.widgets.calibration_plotter import CalibrationPlotterWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Calibration Tool — Submersible Tyrant-AQ")
        self.resize(1320, 900)

        # Internal state
        self.is_recording = False
        self.csv_file = None
        self.csv_writer = None
        self.record_count = 0
        self.record_start_time = None
        self.last_write_time = None
        self.save_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
        os.makedirs(self.save_directory, exist_ok=True)

        self.zoom_factor = 1.0

        # Core Engines
        self.comm_client = CommClient(self)
        self.mock_server = MockCalibrationServer(host="127.0.0.1", port=9001)

        # Timer for recording duration display
        self.ui_timer = QtCore.QTimer()
        self.ui_timer.timeout.connect(self._update_record_timer)

        # Init UI
        self._init_ui()
        self._apply_stylesheet()
        self._connect_signals()

        # Initial UI state
        self._update_connection_ui(False)

    # -------------------------------------------------------------------------
    # Stylesheet & Zoom Handler (Exact WGG Behavior)
    # -------------------------------------------------------------------------
    def _apply_stylesheet(self):
        self.setStyleSheet(get_wgg_stylesheet(self.zoom_factor))

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_factor += 0.1
            else:
                self.zoom_factor -= 0.1
            self.zoom_factor = max(0.6, min(self.zoom_factor, 2.5))
            self._apply_stylesheet()
            event.accept()
        else:
            super().wheelEvent(event)

    # -------------------------------------------------------------------------
    # UI Setup (Direct Layout matching Program-WGG)
    # -------------------------------------------------------------------------
    def _init_ui(self):
        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_main.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout_main.setSpacing(8)

        font_bold = QtGui.QFont()
        font_bold.setBold(True)

        # =====================================================================
        # 1. CONNECTION BAR (USB Serial COM + Ethernet + Mock)
        # =====================================================================
        self.groupBox_connection = QtWidgets.QGroupBox("Connection Settings", self.centralwidget)
        self.hLayout_connection = QtWidgets.QHBoxLayout(self.groupBox_connection)

        # Mode Selector
        self.lbl_mode_label = QtWidgets.QLabel("Mode:", self.groupBox_connection)
        self.hLayout_connection.addWidget(self.lbl_mode_label)

        self.comboBox_mode = QtWidgets.QComboBox(self.groupBox_connection)
        self.comboBox_mode.addItems([
            "Real Hardware (USB Serial / COM)",
            "Real Hardware (Ethernet TCP)",
            "Simulasi (Built-in Mock)"
        ])
        self.comboBox_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.hLayout_connection.addWidget(self.comboBox_mode)

        self.hLayout_connection.addSpacing(10)

        # --- USB Serial Widgets ---
        self.lbl_serial_port = QtWidgets.QLabel("Port:", self.groupBox_connection)
        self.hLayout_connection.addWidget(self.lbl_serial_port)

        self.comboBox_serial_port = QtWidgets.QComboBox(self.groupBox_connection)
        self.comboBox_serial_port.setMinimumWidth(100)
        self.hLayout_connection.addWidget(self.comboBox_serial_port)

        self.btn_refresh_ports = QtWidgets.QPushButton("🔄", self.groupBox_connection)
        self.btn_refresh_ports.setMaximumWidth(32)
        self.btn_refresh_ports.setToolTip("Pindai ulang daftar port COM")
        self.btn_refresh_ports.clicked.connect(self._refresh_serial_ports)
        self.hLayout_connection.addWidget(self.btn_refresh_ports)

        self.lbl_baud_label = QtWidgets.QLabel("Baud:", self.groupBox_connection)
        self.hLayout_connection.addWidget(self.lbl_baud_label)

        self.comboBox_baud = QtWidgets.QComboBox(self.groupBox_connection)
        self.comboBox_baud.addItems(["115200", "9600", "57600", "38400", "19200"])
        self.comboBox_baud.setMaximumWidth(85)
        self.hLayout_connection.addWidget(self.comboBox_baud)

        # --- Ethernet TCP Widgets ---
        self.lbl_ip_label = QtWidgets.QLabel("IP:", self.groupBox_connection)
        self.hLayout_connection.addWidget(self.lbl_ip_label)

        self.lineEdit_ip = QtWidgets.QLineEdit("192.168.1.177", self.groupBox_connection)
        self.lineEdit_ip.setMinimumWidth(110)
        self.hLayout_connection.addWidget(self.lineEdit_ip)

        self.lbl_port_label = QtWidgets.QLabel("Port:", self.groupBox_connection)
        self.hLayout_connection.addWidget(self.lbl_port_label)

        self.lineEdit_port = QtWidgets.QLineEdit("9001", self.groupBox_connection)
        self.lineEdit_port.setMaximumWidth(55)
        self.hLayout_connection.addWidget(self.lineEdit_port)

        self.hLayout_connection.addSpacing(5)

        # Connect Button
        self.btn_connect = QtWidgets.QPushButton("Connect", self.groupBox_connection)
        self.btn_connect.setCheckable(True)
        self.btn_connect.setObjectName("btn_connect")
        self.hLayout_connection.addWidget(self.btn_connect)

        # Status Label
        self.lbl_conn_status = QtWidgets.QLabel("● Disconnected", self.groupBox_connection)
        self.hLayout_connection.addWidget(self.lbl_conn_status)

        spacer_conn = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.hLayout_connection.addItem(spacer_conn)

        self.verticalLayout_main.addWidget(self.groupBox_connection)



        # =====================================================================
        # 2. REAL-TIME SENSOR DATA BAR (Extended for WQ + Motion)
        # =====================================================================
        self.groupBox_realtime = QtWidgets.QGroupBox("Real-Time Sensor Data", self.centralwidget)
        self.vLayout_realtime = QtWidgets.QVBoxLayout(self.groupBox_realtime)
        self.vLayout_realtime.setSpacing(6)

        # Row 1: Water Quality (pH, EC, DO, Temp)
        row1 = QtWidgets.QHBoxLayout()
        lbl_ph_title = QtWidgets.QLabel("pH:", self.groupBox_realtime)
        lbl_ph_title.setFont(font_bold)
        self.lbl_rt_ph = QtWidgets.QLabel("—", self.groupBox_realtime)
        self.lbl_rt_ph.setObjectName("lbl_rt_ph")
        self.lbl_rt_ph.setMinimumWidth(80)

        lbl_ec_title = QtWidgets.QLabel("EC (µS):", self.groupBox_realtime)
        lbl_ec_title.setFont(font_bold)
        self.lbl_rt_ec = QtWidgets.QLabel("—", self.groupBox_realtime)
        self.lbl_rt_ec.setObjectName("lbl_rt_ec")
        self.lbl_rt_ec.setMinimumWidth(80)

        lbl_do_title = QtWidgets.QLabel("DO (mg/L):", self.groupBox_realtime)
        lbl_do_title.setFont(font_bold)
        self.lbl_rt_do = QtWidgets.QLabel("—", self.groupBox_realtime)
        self.lbl_rt_do.setObjectName("lbl_rt_do")
        self.lbl_rt_do.setMinimumWidth(80)

        lbl_temp_title = QtWidgets.QLabel("Temp (°C):", self.groupBox_realtime)
        lbl_temp_title.setFont(font_bold)
        self.lbl_rt_temp = QtWidgets.QLabel("—", self.groupBox_realtime)
        self.lbl_rt_temp.setObjectName("lbl_rt_temp")
        self.lbl_rt_temp.setMinimumWidth(80)

        row1.addWidget(lbl_ph_title)
        row1.addWidget(self.lbl_rt_ph)
        row1.addWidget(lbl_ec_title)
        row1.addWidget(self.lbl_rt_ec)
        row1.addWidget(lbl_do_title)
        row1.addWidget(self.lbl_rt_do)
        row1.addWidget(lbl_temp_title)
        row1.addWidget(self.lbl_rt_temp)
        row1.addStretch()
        self.vLayout_realtime.addLayout(row1)

        # Row 2: Robot Motion & Orientation (Charisto's IMU & Depth)
        row2 = QtWidgets.QHBoxLayout()
        lbl_roll_title = QtWidgets.QLabel("Roll (°):", self.groupBox_realtime)
        lbl_roll_title.setFont(font_bold)
        self.lbl_rt_roll = QtWidgets.QLabel("0.0", self.groupBox_realtime)
        self.lbl_rt_roll.setObjectName("lbl_rt_roll")
        self.lbl_rt_roll.setMinimumWidth(80)

        lbl_pitch_title = QtWidgets.QLabel("Pitch (°):", self.groupBox_realtime)
        lbl_pitch_title.setFont(font_bold)
        self.lbl_rt_pitch = QtWidgets.QLabel("0.0", self.groupBox_realtime)
        self.lbl_rt_pitch.setObjectName("lbl_rt_pitch")
        self.lbl_rt_pitch.setMinimumWidth(80)

        lbl_yaw_title = QtWidgets.QLabel("Heading (°):", self.groupBox_realtime)
        lbl_yaw_title.setFont(font_bold)
        self.lbl_rt_yaw = QtWidgets.QLabel("0.0", self.groupBox_realtime)
        self.lbl_rt_yaw.setObjectName("lbl_rt_yaw")
        self.lbl_rt_yaw.setMinimumWidth(80)

        lbl_depth_title = QtWidgets.QLabel("Kedalaman (m):", self.groupBox_realtime)
        lbl_depth_title.setFont(font_bold)
        self.lbl_rt_depth = QtWidgets.QLabel("0.00", self.groupBox_realtime)
        self.lbl_rt_depth.setObjectName("lbl_rt_depth")
        self.lbl_rt_depth.setMinimumWidth(80)

        row2.addWidget(lbl_roll_title)
        row2.addWidget(self.lbl_rt_roll)
        row2.addWidget(lbl_pitch_title)
        row2.addWidget(self.lbl_rt_pitch)
        row2.addWidget(lbl_yaw_title)
        row2.addWidget(self.lbl_rt_yaw)
        row2.addWidget(lbl_depth_title)
        row2.addWidget(self.lbl_rt_depth)
        row2.addStretch()
        self.vLayout_realtime.addLayout(row2)

        self.verticalLayout_main.addWidget(self.groupBox_realtime)

        # =====================================================================
        # 3. CALIBRATION CONTROLS (Grouped into Tabs)
        # =====================================================================

        # --- GroupBox EC Calibration (Primary Task) ---
        self.groupBox_ec = QtWidgets.QGroupBox("Conductivity Calibration (Atlas Scientific EZO-EC™)", self.centralwidget)
        self.vLayout_ec = QtWidgets.QVBoxLayout(self.groupBox_ec)
        self.vLayout_ec.setSpacing(6)

        self.lbl_ec_status = QtWidgets.QLabel("Calibration Status: Unknown", self.groupBox_ec)
        self.vLayout_ec.addWidget(self.lbl_ec_status)

        # EC Dry (Mandatory First Step)
        self.btn_ec_dry = QtWidgets.QPushButton("Cal Dry (Wajib Dilakukan Pertama)", self.groupBox_ec)
        self.btn_ec_dry.setObjectName("btn_ec_dry")
        self.btn_ec_dry.setToolTip("Datasheet EZO-EC Hal. 22 & 68: Kalibrasi udara kering wajib dilakukan pertama kali sebelum probe dicelupkan ke larutan!")
        self.vLayout_ec.addWidget(self.btn_ec_dry)

        # EC Value Input + One Point
        hLayout_ec_val = QtWidgets.QHBoxLayout()
        lbl_ec_val_label = QtWidgets.QLabel("Larutan Standar (µS/cm):", self.groupBox_ec)
        self.lineEdit_ec_value = QtWidgets.QLineEdit("1413", self.groupBox_ec)
        self.lineEdit_ec_value.setMaximumWidth(80)
        self.btn_ec_one = QtWidgets.QPushButton("Cal One Point", self.groupBox_ec)
        self.btn_ec_one.setObjectName("btn_ec_one")
        self.btn_ec_one.setToolTip("Datasheet Hal. 69: Celupkan ke larutan standar, kocok perlahan untuk membuang gelembung udara, tunggu grafik stabil lalu klik.")
        hLayout_ec_val.addWidget(lbl_ec_val_label)
        hLayout_ec_val.addWidget(self.lineEdit_ec_value)
        hLayout_ec_val.addWidget(self.btn_ec_one)
        self.vLayout_ec.addLayout(hLayout_ec_val)

        # EC Low + High
        hLayout_ec_sub = QtWidgets.QHBoxLayout()
        self.btn_ec_low = QtWidgets.QPushButton("Cal Low (12880)", self.groupBox_ec)
        self.btn_ec_low.setObjectName("btn_ec_low")
        self.btn_ec_low.setToolTip("Datasheet Hal. 70: Kalibrasi rentang rendah (misal 12.880 µS/cm)")
        self.btn_ec_high = QtWidgets.QPushButton("Cal High (80000)", self.groupBox_ec)
        self.btn_ec_high.setObjectName("btn_ec_high")
        self.btn_ec_high.setToolTip("Datasheet Hal. 70: Kalibrasi rentang tinggi (misal 80.000 µS/cm)")
        hLayout_ec_sub.addWidget(self.btn_ec_low)
        hLayout_ec_sub.addWidget(self.btn_ec_high)
        self.vLayout_ec.addLayout(hLayout_ec_sub)

        # EC Status + Clear
        hLayout_ec_act = QtWidgets.QHBoxLayout()
        self.btn_ec_status = QtWidgets.QPushButton("Check Status (?)", self.groupBox_ec)
        self.btn_ec_status.setToolTip("Datasheet Hal. 22: Cek status respon (?CAL,0 / ?CAL,1 / ?CAL,2)")
        self.btn_ec_clear = QtWidgets.QPushButton("Clear Calibration", self.groupBox_ec)
        self.btn_ec_clear.setObjectName("btn_ec_clear")
        self.btn_ec_clear.setToolTip("Hapus kalibrasi EC di memori dan kembalikan ke default pabrik")
        hLayout_ec_act.addWidget(self.btn_ec_status)
        hLayout_ec_act.addWidget(self.btn_ec_clear)
        self.vLayout_ec.addLayout(hLayout_ec_act)

        # --- GroupBox pH Calibration ---
        self.groupBox_ph = QtWidgets.QGroupBox("pH Calibration (Atlas Scientific EZO)", self.centralwidget)
        self.vLayout_ph = QtWidgets.QVBoxLayout(self.groupBox_ph)
        self.vLayout_ph.setSpacing(6)

        self.lbl_ph_status = QtWidgets.QLabel("Calibration Status: Unknown", self.groupBox_ph)
        self.vLayout_ph.addWidget(self.lbl_ph_status)

        self.btn_ph_mid = QtWidgets.QPushButton("Cal Mid (pH 7.00)", self.groupBox_ph)
        self.btn_ph_mid.setObjectName("btn_ph_mid")
        self.vLayout_ph.addWidget(self.btn_ph_mid)

        hLayout_ph_sub = QtWidgets.QHBoxLayout()
        self.btn_ph_low = QtWidgets.QPushButton("Cal Low (pH 4.00)", self.groupBox_ph)
        self.btn_ph_low.setObjectName("btn_ph_low")
        self.btn_ph_high = QtWidgets.QPushButton("Cal High (pH 10.00)", self.groupBox_ph)
        self.btn_ph_high.setObjectName("btn_ph_high")
        hLayout_ph_sub.addWidget(self.btn_ph_low)
        hLayout_ph_sub.addWidget(self.btn_ph_high)
        self.vLayout_ph.addLayout(hLayout_ph_sub)

        hLayout_ph_act = QtWidgets.QHBoxLayout()
        self.btn_ph_status = QtWidgets.QPushButton("Check Status", self.groupBox_ph)
        self.btn_ph_clear = QtWidgets.QPushButton("Clear Calibration", self.groupBox_ph)
        self.btn_ph_clear.setObjectName("btn_ph_clear")
        hLayout_ph_act.addWidget(self.btn_ph_status)
        hLayout_ph_act.addWidget(self.btn_ph_clear)
        self.vLayout_ph.addLayout(hLayout_ph_act)

        # --- GroupBox DO Calibration ---
        self.groupBox_do = QtWidgets.QGroupBox("Dissolved Oxygen — DO (DFRobot / EZO)", self.centralwidget)
        self.vLayout_do = QtWidgets.QVBoxLayout(self.groupBox_do)
        self.vLayout_do.setSpacing(6)

        self.lbl_do_status = QtWidgets.QLabel("Status: Siap kalibrasi", self.groupBox_do)
        self.vLayout_do.addWidget(self.lbl_do_status)

        hLayout_do_btns = QtWidgets.QHBoxLayout()
        self.btn_do_sat = QtWidgets.QPushButton("Cal 100% Saturation", self.groupBox_do)
        self.btn_do_zero = QtWidgets.QPushButton("Cal Zero DO", self.groupBox_do)
        self.btn_do_clear = QtWidgets.QPushButton("Clear", self.groupBox_do)
        self.btn_do_clear.setObjectName("btn_do_clear")
        hLayout_do_btns.addWidget(self.btn_do_sat)
        hLayout_do_btns.addWidget(self.btn_do_zero)
        hLayout_do_btns.addWidget(self.btn_do_clear)
        self.vLayout_do.addLayout(hLayout_do_btns)

        self.lbl_do_info = QtWidgets.QLabel(
            "Kalibrasi 100% di udara lembap jenuh.\n"
            "Kalibrasi 0% menggunakan larutan Na2SO3 5%.\n"
            "Data tersimpan otomatis ke memori mikrokontroler.", self.groupBox_do
        )
        self.lbl_do_info.setStyleSheet("color: #a5adcb; font-size: 11px;")
        self.vLayout_do.addWidget(self.lbl_do_info)

        # --- GroupBox Temperature (Atlas Scientific Surveyor™ RTD PT-1000) ---
        self.groupBox_temp = QtWidgets.QGroupBox("Temperature Calibration (Atlas Scientific Surveyor™ RTD)", self.centralwidget)
        self.vLayout_temp = QtWidgets.QVBoxLayout(self.groupBox_temp)
        self.vLayout_temp.setSpacing(6)

        self.lbl_temp_status = QtWidgets.QLabel("Status: Siap kalibrasi suhu", self.groupBox_temp)
        self.vLayout_temp.addWidget(self.lbl_temp_status)

        # Row 1: Ice Bath 0°C Quick Calibrate
        hLayout_temp_r1 = QtWidgets.QHBoxLayout()
        self.btn_temp_ice = QtWidgets.QPushButton("● Cal Ice Bath (0.0 °C)", self.groupBox_temp)
        self.btn_temp_ice.setObjectName("btn_temp_ice")
        self.btn_temp_ice.setToolTip("Kalibrasi titik nol es (0 °C) untuk mengunci tegangan offset (nominal 1.058 V)")
        hLayout_temp_r1.addWidget(self.btn_temp_ice)
        self.vLayout_temp.addLayout(hLayout_temp_r1)

        # Row 2: Custom Reference Temperature Input
        hLayout_temp_r2 = QtWidgets.QHBoxLayout()
        lbl_temp_ref = QtWidgets.QLabel("Suhu Acuan (°C):", self.groupBox_temp)
        self.lineEdit_temp_val = QtWidgets.QLineEdit("25.0", self.groupBox_temp)
        self.lineEdit_temp_val.setMaximumWidth(70)
        self.lineEdit_temp_val.setPlaceholderText("25.0")
        self.btn_temp_custom = QtWidgets.QPushButton("Kalibrasi 1-Point", self.groupBox_temp)
        self.btn_temp_custom.setObjectName("btn_temp_custom")
        hLayout_temp_r2.addWidget(lbl_temp_ref)
        hLayout_temp_r2.addWidget(self.lineEdit_temp_val)
        hLayout_temp_r2.addWidget(self.btn_temp_custom)
        self.vLayout_temp.addLayout(hLayout_temp_r2)

        # Row 3: Check Status & Reset
        hLayout_temp_r3 = QtWidgets.QHBoxLayout()
        self.btn_temp_status = QtWidgets.QPushButton("Check Status", self.groupBox_temp)
        self.btn_temp_clear = QtWidgets.QPushButton("Clear Calibration", self.groupBox_temp)
        self.btn_temp_clear.setObjectName("btn_temp_clear")
        hLayout_temp_r3.addWidget(self.btn_temp_status)
        hLayout_temp_r3.addWidget(self.btn_temp_clear)
        self.vLayout_temp.addLayout(hLayout_temp_r3)

        self.lbl_temp_info = QtWidgets.QLabel(
            "Atlas Surveyor™ RTD (PT-1000 Class B Platinum):\n"
            "Rumus Datasheet: °C = (V - 1.058) / 0.009  (9 mV/°C)\n"
            "Gunakan metode Ice Bath 0°C untuk akurasi tertinggi.", self.groupBox_temp
        )
        self.lbl_temp_info.setStyleSheet("color: #a5adcb; font-size: 11px;")
        self.vLayout_temp.addWidget(self.lbl_temp_info)

        # --- GroupBox Motion & Depth ---
        self.groupBox_motion = QtWidgets.QGroupBox("Orientasi & Gerak Wahana (IMU & Depth)", self.centralwidget)
        self.vLayout_motion = QtWidgets.QVBoxLayout(self.groupBox_motion)
        self.vLayout_motion.setSpacing(6)

        self.lbl_motion_status = QtWidgets.QLabel("Status: Wahana siap dikalibrasi", self.groupBox_motion)
        self.vLayout_motion.addWidget(self.lbl_motion_status)

        self.btn_gyro_cal = QtWidgets.QPushButton("Calibrate Gyro Bias (Wahana Diam)", self.groupBox_motion)
        self.btn_gyro_cal.setObjectName("btn_gyro_cal")
        self.vLayout_motion.addWidget(self.btn_gyro_cal)

        self.btn_level_tare = QtWidgets.QPushButton("Tare Horizon (Roll & Pitch = 0°)", self.groupBox_motion)
        self.btn_level_tare.setObjectName("btn_level_tare")
        self.vLayout_motion.addWidget(self.btn_level_tare)

        hLayout_mag = QtWidgets.QHBoxLayout()
        self.btn_mag_stream = QtWidgets.QPushButton("Mulai Putar 360°", self.groupBox_motion)
        self.btn_mag_stream.setObjectName("btn_mag_stream")
        self.btn_mag_save = QtWidgets.QPushButton("Simpan EEPROM", self.groupBox_motion)
        hLayout_mag.addWidget(self.btn_mag_stream)
        hLayout_mag.addWidget(self.btn_mag_save)
        self.vLayout_motion.addLayout(hLayout_mag)

        self.btn_depth_tare = QtWidgets.QPushButton("Tare Kedalaman Permukaan (Z = 0.0 m)", self.groupBox_motion)
        self.btn_depth_tare.setObjectName("btn_depth_tare")
        self.vLayout_motion.addWidget(self.btn_depth_tare)

        hLayout_dens = QtWidgets.QHBoxLayout()
        lbl_dens = QtWidgets.QLabel("Densitas Air (kg/m³):", self.groupBox_motion)
        self.lineEdit_density = QtWidgets.QLineEdit("997.0", self.groupBox_motion)
        self.lineEdit_density.setMaximumWidth(70)
        self.btn_set_density = QtWidgets.QPushButton("Set", self.groupBox_motion)
        self.btn_set_density.setMaximumWidth(50)
        hLayout_dens.addWidget(lbl_dens)
        hLayout_dens.addWidget(self.lineEdit_density)
        hLayout_dens.addWidget(self.btn_set_density)
        self.vLayout_motion.addLayout(hLayout_dens)

        self.lbl_motion_info = QtWidgets.QLabel(
            "Panduan:\n"
            "1. Diamkan robot di permukaan datar untuk Gyro & Leveling.\n"
            "2. Putar 360° untuk kalibrasi kompas magnetometer.\n"
            "3. Lakukan tare kedalaman saat robot mengapung di waduk.", self.groupBox_motion
        )
        self.lbl_motion_info.setStyleSheet("color: #a5adcb; font-size: 11px;")
        self.vLayout_motion.addWidget(self.lbl_motion_info)

        # =====================================================================
        # 4. MAIN WORKSPACE: QSplitter (Left: Tabs, Right: Real-time Plotter)
        # =====================================================================
        self.splitter_center = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self.centralwidget)

        # Tab Widget for Calibration Controls
        self.tabWidget_cal = QtWidgets.QTabWidget(self.splitter_center)
        self.tabWidget_cal.setMinimumWidth(430)

        # Tab 1: Kualitas Air
        tab_wq = QtWidgets.QWidget()
        scroll_wq = QtWidgets.QScrollArea(tab_wq)
        scroll_wq.setWidgetResizable(True)
        scroll_wq.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_wq_content = QtWidgets.QWidget()
        vLayout_wq = QtWidgets.QVBoxLayout(scroll_wq_content)
        vLayout_wq.setContentsMargins(4, 4, 4, 4)
        vLayout_wq.setSpacing(8)

        vLayout_wq.addWidget(self.groupBox_ec)
        vLayout_wq.addWidget(self.groupBox_ph)
        vLayout_wq.addWidget(self.groupBox_do)
        vLayout_wq.addWidget(self.groupBox_temp)
        vLayout_wq.addStretch()
        scroll_wq.setWidget(scroll_wq_content)

        layout_wq_outer = QtWidgets.QVBoxLayout(tab_wq)
        layout_wq_outer.setContentsMargins(0, 0, 0, 0)
        layout_wq_outer.addWidget(scroll_wq)
        self.tabWidget_cal.addTab(tab_wq, "1. Kualitas Air (EC, pH, DO, Suhu)")

        # Tab 2: Orientasi & Gerak Wahana
        tab_motion = QtWidgets.QWidget()
        scroll_motion = QtWidgets.QScrollArea(tab_motion)
        scroll_motion.setWidgetResizable(True)
        scroll_motion.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_motion_content = QtWidgets.QWidget()
        vLayout_m = QtWidgets.QVBoxLayout(scroll_motion_content)
        vLayout_m.setContentsMargins(4, 4, 4, 4)
        vLayout_m.setSpacing(8)

        vLayout_m.addWidget(self.groupBox_motion)
        vLayout_m.addStretch()
        scroll_motion.setWidget(scroll_motion_content)

        layout_m_outer = QtWidgets.QVBoxLayout(tab_motion)
        layout_m_outer.setContentsMargins(0, 0, 0, 0)
        layout_m_outer.addWidget(scroll_motion)
        self.tabWidget_cal.addTab(tab_motion, "2. Orientasi & Gerak (Wahana)")

        # Right Panel: Interactive Calibration Plotter
        self.cal_plotter = CalibrationPlotterWidget(self.splitter_center)

        self.splitter_center.addWidget(self.tabWidget_cal)
        self.splitter_center.addWidget(self.cal_plotter)
        self.splitter_center.setStretchFactor(0, 4)
        self.splitter_center.setStretchFactor(1, 6)

        self.verticalLayout_main.addWidget(self.splitter_center, stretch=1)

        # =====================================================================
        # 4. COMMUNICATION LOG (Exact WGG Style)
        # =====================================================================
        self.groupBox_log = QtWidgets.QGroupBox("Communication Log", self.centralwidget)
        self.vLayout_log = QtWidgets.QVBoxLayout(self.groupBox_log)

        self.textBrowser_log = QtWidgets.QTextBrowser(self.groupBox_log)
        self.textBrowser_log.setMinimumHeight(120)
        self.vLayout_log.addWidget(self.textBrowser_log)

        self.btn_clear_log = QtWidgets.QPushButton("Clear Log", self.groupBox_log)
        self.btn_clear_log.setMaximumWidth(120)
        self.vLayout_log.addWidget(self.btn_clear_log)

        self.verticalLayout_main.addWidget(self.groupBox_log)

        # =====================================================================
        # 5. DATA RECORDING BAR (Exact WGG Style)
        # =====================================================================
        self.groupBox_record = QtWidgets.QGroupBox("Data Recording", self.centralwidget)
        self.hLayout_record = QtWidgets.QHBoxLayout(self.groupBox_record)

        self.btn_record = QtWidgets.QPushButton("● Record", self.groupBox_record)
        self.btn_record.setCheckable(True)
        self.btn_record.setObjectName("btn_record")
        self.hLayout_record.addWidget(self.btn_record)

        self.lineEdit_savepath = QtWidgets.QLineEdit(self.groupBox_record)
        self.lineEdit_savepath.setReadOnly(True)
        self.lineEdit_savepath.setPlaceholderText("Save path...")
        self.hLayout_record.addWidget(self.lineEdit_savepath)

        self.btn_browse = QtWidgets.QPushButton("Browse...", self.groupBox_record)
        self.btn_browse.setMaximumWidth(90)
        self.hLayout_record.addWidget(self.btn_browse)

        self.lbl_interval_label = QtWidgets.QLabel("Interval Rekam:", self.groupBox_record)
        self.hLayout_record.addWidget(self.lbl_interval_label)

        self.doubleSpinBox_interval = QtWidgets.QDoubleSpinBox(self.groupBox_record)
        self.doubleSpinBox_interval.setMinimum(0.0)
        self.doubleSpinBox_interval.setMaximum(3600.0)
        self.doubleSpinBox_interval.setSingleStep(0.5)
        self.doubleSpinBox_interval.setValue(1.0)
        self.doubleSpinBox_interval.setSuffix(" s")
        self.hLayout_record.addWidget(self.doubleSpinBox_interval)

        self.lbl_record_status = QtWidgets.QLabel("Status: Idle", self.groupBox_record)
        self.hLayout_record.addWidget(self.lbl_record_status)

        self.verticalLayout_main.addWidget(self.groupBox_record)
        
        # Populate serial ports and initialize default USB Serial mode
        self._refresh_serial_ports()
        self._on_mode_changed(0)

    # -------------------------------------------------------------------------
    # Signal Connections
    # -------------------------------------------------------------------------
    def _connect_signals(self):
        # Connection
        self.btn_connect.clicked.connect(self._on_connect_toggle)

        # pH Calibration
        self.btn_ph_mid.clicked.connect(lambda: self._send_cal_command("CAL_PH,mid,7.00"))
        self.btn_ph_low.clicked.connect(lambda: self._send_cal_command("CAL_PH,low,4.00"))
        self.btn_ph_high.clicked.connect(lambda: self._send_cal_command("CAL_PH,high,10.00"))
        self.btn_ph_status.clicked.connect(lambda: self._send_cal_command("CAL_PH,?"))
        self.btn_ph_clear.clicked.connect(lambda: self._confirm_and_send("CAL_PH,clear",
            "Apakah Anda yakin ingin menghapus kalibrasi pH?"))

        # EC Calibration
        self.btn_ec_dry.clicked.connect(lambda: self._send_cal_command("CAL_EC,dry"))
        self.btn_ec_one.clicked.connect(self._on_ec_one)
        self.btn_ec_low.clicked.connect(self._on_ec_low)
        self.btn_ec_high.clicked.connect(self._on_ec_high)
        self.btn_ec_status.clicked.connect(lambda: self._send_cal_command("CAL_EC,?"))
        self.btn_ec_clear.clicked.connect(lambda: self._confirm_and_send("CAL_EC,clear",
            "Apakah Anda yakin ingin menghapus kalibrasi EC?"))

        # DO Calibration
        self.btn_do_sat.clicked.connect(lambda: self._send_cal_command("CAL_DO,sat,100"))
        self.btn_do_zero.clicked.connect(lambda: self._send_cal_command("CAL_DO,zero"))
        self.btn_do_clear.clicked.connect(lambda: self._confirm_and_send("CAL_DO,clear",
            "Apakah Anda yakin ingin menghapus kalibrasi DO?"))

        # Temperature Calibration (Atlas Surveyor RTD PT-1000)
        self.btn_temp_ice.clicked.connect(lambda: self._send_cal_command("CAL_TEMP,ice,0.0"))
        self.btn_temp_custom.clicked.connect(self._on_temp_custom)
        self.btn_temp_status.clicked.connect(lambda: self._send_cal_command("CAL_TEMP,?"))
        self.btn_temp_clear.clicked.connect(lambda: self._confirm_and_send("CAL_TEMP,clear",
            "Apakah Anda yakin ingin mereset kalibrasi suhu ke default pabrik (1.058V, 9mV/°C)?"))

        # Robot Motion & Orientation (Charisto)
        self.btn_gyro_cal.clicked.connect(lambda: self._send_cal_command("CAL_IMU,gyro"))
        self.btn_level_tare.clicked.connect(lambda: self._send_cal_command("CAL_IMU,level"))
        self.btn_mag_stream.clicked.connect(self._toggle_mag_stream)
        self.btn_mag_save.clicked.connect(lambda: self._send_cal_command("CAL_MAG,save"))
        self.btn_depth_tare.clicked.connect(lambda: self._send_cal_command("CAL_DEPTH,tare"))
        self.btn_set_density.clicked.connect(self._on_set_density)

        # Recording
        self.btn_record.clicked.connect(self._on_record_toggle)
        self.btn_browse.clicked.connect(self._on_browse)

        # Log
        self.btn_clear_log.clicked.connect(self.textBrowser_log.clear)

        # Comm Client signals
        self.comm_client.connection_changed.connect(self._on_client_conn_changed)
        self.comm_client.telemetry_received.connect(self._on_telemetry_received)
        self.comm_client.cal_response_received.connect(self._on_cal_response_received)
        self.comm_client.log_message.connect(self._log)

        # Tab change signal (sync graph channel)
        self.tabWidget_cal.currentChanged.connect(self._on_cal_tab_changed)

    # -------------------------------------------------------------------------
    # Mode & Connection Management
    # -------------------------------------------------------------------------
    def _refresh_serial_ports(self):
        curr = self.comboBox_serial_port.currentText()
        self.comboBox_serial_port.clear()
        ports = self.comm_client.get_available_ports()
        if ports:
            self.comboBox_serial_port.addItems(ports)
            if curr in ports:
                self.comboBox_serial_port.setCurrentText(curr)
        else:
            self.comboBox_serial_port.addItem("Tidak ada COM")

    def _on_mode_changed(self, idx: int):
        self.mock_server.stop()
        if idx == 0:  # USB Serial / COM
            self.lbl_serial_port.setVisible(True)
            self.comboBox_serial_port.setVisible(True)
            self.btn_refresh_ports.setVisible(True)
            self.lbl_baud_label.setVisible(True)
            self.comboBox_baud.setVisible(True)

            self.lbl_ip_label.setVisible(False)
            self.lineEdit_ip.setVisible(False)
            self.lbl_port_label.setVisible(False)
            self.lineEdit_port.setVisible(False)
            self._log("Mode diubah ke: Real Hardware (USB Serial / COM).")
        elif idx == 1:  # Ethernet TCP
            self.lbl_serial_port.setVisible(False)
            self.comboBox_serial_port.setVisible(False)
            self.btn_refresh_ports.setVisible(False)
            self.lbl_baud_label.setVisible(False)
            self.comboBox_baud.setVisible(False)

            self.lbl_ip_label.setVisible(True)
            self.lineEdit_ip.setVisible(True)
            self.lineEdit_ip.setEnabled(True)
            self.lineEdit_ip.setText("192.168.1.177")
            self.lbl_port_label.setVisible(True)
            self.lineEdit_port.setVisible(True)
            self.lineEdit_port.setEnabled(True)
            self._log("Mode diubah ke: Real Hardware (Ethernet TCP).")
        elif idx == 2:  # Mock Simulation
            self.lbl_serial_port.setVisible(False)
            self.comboBox_serial_port.setVisible(False)
            self.btn_refresh_ports.setVisible(False)
            self.lbl_baud_label.setVisible(False)
            self.comboBox_baud.setVisible(False)

            self.lbl_ip_label.setVisible(True)
            self.lineEdit_ip.setVisible(True)
            self.lineEdit_ip.setText("127.0.0.1")
            self.lineEdit_ip.setEnabled(False)
            self.lbl_port_label.setVisible(True)
            self.lineEdit_port.setVisible(True)
            self.lineEdit_port.setEnabled(False)
            self.mock_server.start()
            self._log("Mode diubah ke: Simulasi (Built-in Mock).")

    def _on_connect_toggle(self, checked: bool):
        if checked:
            mode_idx = self.comboBox_mode.currentIndex()
            if mode_idx == 0:  # USB Serial / COM
                port = self.comboBox_serial_port.currentText().strip()
                if not port or port == "Tidak ada COM":
                    self._log("ERROR: Port COM tidak terdeteksi. Silakan tancapkan kabel USB lalu klik tombol 🔄.")
                    self.btn_connect.setChecked(False)
                    return
                baud_str = self.comboBox_baud.currentText().strip()
                try:
                    baud = int(baud_str)
                except ValueError:
                    baud = 115200
                self.comm_client.connect_to_serial(port, baud)

            elif mode_idx == 1:  # Ethernet TCP
                ip = self.lineEdit_ip.text().strip()
                port_str = self.lineEdit_port.text().strip()
                try:
                    port = int(port_str)
                except ValueError:
                    self._log("ERROR: Port IP tidak valid.")
                    self.btn_connect.setChecked(False)
                    return
                self.comm_client.connect_to_host(ip, port)

            elif mode_idx == 2:  # Mock
                self.mock_server.start()
                self.comm_client.connect_to_host("127.0.0.1", 9001)
        else:
            self.comm_client.disconnect_from_host()

    def _on_client_conn_changed(self, connected: bool, message: str):
        self._update_connection_ui(connected)

    def _update_connection_ui(self, connected: bool):
        if connected:
            if self.comm_client.conn_type == "SERIAL":
                self.lbl_conn_status.setText(f"● Connected ({self.comm_client.serial_port})")
            else:
                self.lbl_conn_status.setText(f"● Connected ({self.comm_client.host}:{self.comm_client.port})")
            self.lbl_conn_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
            self.btn_connect.setText("Disconnect")
            self.btn_connect.setChecked(True)
            self.comboBox_mode.setEnabled(False)
            self.comboBox_serial_port.setEnabled(False)
            self.btn_refresh_ports.setEnabled(False)
            self.comboBox_baud.setEnabled(False)
            self.lineEdit_ip.setEnabled(False)
            self.lineEdit_port.setEnabled(False)
        else:
            self.lbl_conn_status.setText("● Disconnected")
            self.lbl_conn_status.setStyleSheet("color: #CCCCCC; font-weight: bold;")
            self.btn_connect.setText("Connect")
            self.btn_connect.setChecked(False)
            self.comboBox_mode.setEnabled(True)
            self.comboBox_serial_port.setEnabled(True)
            self.btn_refresh_ports.setEnabled(True)
            self.comboBox_baud.setEnabled(True)
            self.lineEdit_ip.setEnabled(True)
            self.lineEdit_port.setEnabled(True)

    def _on_cal_tab_changed(self, idx: int):
        if idx == 0:
            # Switched to Water Quality tab -> ensure EC is default plotted if on motion
            if self.cal_plotter.current_channel_key in ("DEPTH", "ROLL", "PITCH"):
                self.cal_plotter.combo_channel.setCurrentIndex(0)  # EC
        elif idx == 1:
            # Switched to Motion tab -> switch plotter to Depth
            if self.cal_plotter.current_channel_key in ("EC", "PH", "DO", "TEMP"):
                for i in range(self.cal_plotter.combo_channel.count()):
                    if self.cal_plotter.combo_channel.itemData(i) == "DEPTH":
                        self.cal_plotter.combo_channel.setCurrentIndex(i)
                        break

    # -------------------------------------------------------------------------
    # Telemetry & Calibration Response
    # -------------------------------------------------------------------------
    def _on_telemetry_received(self, data: dict):
        ph_val = f"{data.get('ph', 0.0):.2f}"
        ec_val = f"{data.get('ec', 0.0):.1f}"
        do_val = f"{data.get('do', 0.0):.2f}"
        temp_val = f"{data.get('temp', 0.0):.2f}"
        roll_val = f"{data.get('roll', 0.0):+.1f}"
        pitch_val = f"{data.get('pitch', 0.0):+.1f}"
        yaw_val = f"{data.get('yaw', 0.0):.1f}"
        depth_val = f"{data.get('depth', 0.0):.2f}"

        # Update labels
        self.lbl_rt_ph.setText(ph_val)
        self.lbl_rt_ec.setText(ec_val)
        self.lbl_rt_do.setText(do_val)
        self.lbl_rt_temp.setText(temp_val)
        self.lbl_rt_roll.setText(roll_val)
        self.lbl_rt_pitch.setText(pitch_val)
        self.lbl_rt_yaw.setText(yaw_val)
        self.lbl_rt_depth.setText(depth_val)

        # High-contrast white sensor values
        self.lbl_rt_ph.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_ec.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_do.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_temp.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_roll.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_pitch.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_yaw.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.lbl_rt_depth.setStyleSheet("color: #FFFFFF; font-weight: bold;")

        # Update Real-Time Calibration Plotter
        self.cal_plotter.add_telemetry(data)

        # CSV Recording
        if self.is_recording and self.csv_writer:
            current_time = datetime.now()
            interval = self.doubleSpinBox_interval.value()

            if self.last_write_time is None or (current_time - self.last_write_time).total_seconds() >= interval:
                now_str = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.csv_writer.writerow([
                    now_str, data.get("ts", 0),
                    ph_val, ec_val, do_val, temp_val,
                    roll_val, pitch_val, yaw_val, depth_val
                ])
                self.csv_file.flush()
                self.record_count += 1
                self.last_write_time = current_time
                self._update_status_display()

    def _on_cal_response_received(self, sensor: str, response: str):
        if sensor == "PH":
            self.lbl_ph_status.setText(f"Calibration Status: {response}")
            self.lbl_ph_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "EC":
            self.lbl_ec_status.setText(f"Calibration Status: {response}")
            self.lbl_ec_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "DO":
            self.lbl_do_status.setText(f"Calibration Status: {response}")
            self.lbl_do_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "TEMP":
            self.lbl_temp_status.setText(f"Calibration Status: {response}")
            self.lbl_temp_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor in ("IMU", "MAG", "DEPTH"):
            self.lbl_motion_status.setText(f"Status ({sensor}): {response}")
            self.lbl_motion_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")

    # -------------------------------------------------------------------------
    # Command Sending & Confirmation
    # -------------------------------------------------------------------------
    def _send_cal_command(self, cmd: str):
        if not self.comm_client.is_connected:
            self._log("ERROR: Belum terhubung ke Teensy.")
            return
        self.comm_client.send_command(cmd)

    def _confirm_and_send(self, cmd: str, message: str):
        reply = QtWidgets.QMessageBox.question(
            self, "Konfirmasi", message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self._send_cal_command(cmd)

    # -------------------------------------------------------------------------
    # EC & Motion Helpers
    # -------------------------------------------------------------------------
    def _get_ec_value(self) -> str:
        val = self.lineEdit_ec_value.text().strip()
        if not val:
            self._log("ERROR: Masukkan nilai larutan EC terlebih dahulu.")
            return ""
        try:
            float(val)
        except ValueError:
            self._log("ERROR: Nilai EC tidak valid (harus angka).")
            return ""
        return val

    def _on_ec_one(self):
        val = self._get_ec_value()
        if val:
            self._send_cal_command(f"CAL_EC,one,{val}")

    def _on_ec_low(self):
        val = self._get_ec_value()
        if val:
            self._send_cal_command(f"CAL_EC,low,{val}")

    def _on_ec_high(self):
        val = self._get_ec_value()
        if val:
            self._send_cal_command(f"CAL_EC,high,{val}")

    def _on_temp_custom(self):
        val = self.lineEdit_temp_val.text().strip()
        if not val:
            self._log("ERROR: Masukkan nilai suhu acuan terlebih dahulu.")
            return
        try:
            t_val = float(val)
            self._send_cal_command(f"CAL_TEMP,cal,{t_val:.2f}")
        except ValueError:
            self._log("ERROR: Nilai suhu acuan tidak valid (harus angka numerik).")

    def _toggle_mag_stream(self):
        if self.btn_mag_stream.text() == "Mulai Putar 360°":
            self.btn_mag_stream.setText("Berhenti Putar")
            self._send_cal_command("CAL_MAG,start")
        else:
            self.btn_mag_stream.setText("Mulai Putar 360°")
            self._send_cal_command("CAL_MAG,stop")

    def _on_set_density(self):
        val = self.lineEdit_density.text().strip()
        try:
            d_val = float(val)
            self._send_cal_command(f"CAL_DEPTH,density,{d_val:.1f}")
        except ValueError:
            self._log("ERROR: Nilai densitas air tidak valid.")

    # -------------------------------------------------------------------------
    # Recording Functions (Exact WGG Logic)
    # -------------------------------------------------------------------------
    def _on_record_toggle(self, checked: bool):
        if checked:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        if not self.comm_client.is_connected:
            self._log("ERROR: Connect to Teensy before recording.")
            self.btn_record.setChecked(False)
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"calibration_{timestamp_str}.csv"
        filepath = os.path.join(self.save_directory, filename)

        try:
            self.csv_file = open(filepath, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([
                "Datetime", "Teensy_ms",
                "pH", "Conductivity_uS", "DO_mgL", "Temperature_C",
                "Roll_deg", "Pitch_deg", "Yaw_deg", "Depth_m"
            ])
            self.csv_file.flush()
            self.is_recording = True
            self.record_count = 0
            self.record_start_time = datetime.now()
            self.last_write_time = None
            self.doubleSpinBox_interval.setEnabled(False)
            self.ui_timer.start(1000)
            self.lbl_record_status.setText("Status: Recording... (00:00:00)")
            self.lbl_record_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
            self.btn_record.setText("■ Stop")
            self.lineEdit_savepath.setText(filepath)
            self._log(f"Recording started: {filepath} with interval {self.doubleSpinBox_interval.value()}s")
        except Exception as e:
            self._log(f"ERROR: Cannot create CSV — {e}")
            self.btn_record.setChecked(False)

    def _stop_recording(self):
        self.is_recording = False
        self.ui_timer.stop()
        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
            self.csv_writer = None
        self.lbl_record_status.setText(f"Status: Idle (saved {self.record_count} samples)")
        self.lbl_record_status.setStyleSheet("color: #E0E0E0;")
        self.btn_record.setText("● Record")
        self.doubleSpinBox_interval.setEnabled(True)
        self._log(f"Recording stopped. Total samples: {self.record_count}")

    def _update_record_timer(self):
        self._update_status_display()

    def _update_status_display(self):
        if self.is_recording and self.record_start_time:
            elapsed = datetime.now() - self.record_start_time
            total_seconds = int(elapsed.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.lbl_record_status.setText(f"Status: Recording... ({time_str} | {self.record_count} samples)")

    def _on_browse(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Save Directory", self.save_directory
        )
        if directory:
            self.save_directory = directory
            self._log(f"Save directory: {directory}")

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.textBrowser_log.append(f"[{timestamp}] {message}")
        sb = self.textBrowser_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # -------------------------------------------------------------------------
    # Close Event
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        if self.is_recording:
            self._stop_recording()
        if self.comm_client.is_connected:
            self.comm_client.disconnect_from_host()
        if self.mock_server.running:
            self.mock_server.stop()
        event.accept()
