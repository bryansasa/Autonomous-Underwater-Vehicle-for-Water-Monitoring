# -*- coding: utf-8 -*-
"""
Tab 1: Water Quality Sensor Calibration (Bryan/Yen)
Supports pH, EC, Dissolved Oxygen, and Temperature Calibration.
"""

from PyQt5 import QtWidgets, QtCore, QtGui
from ui.widgets.metric_card import MetricCard
from ui.widgets.stability_plotter import StabilityPlotterWidget


class WaterQualityTab(QtWidgets.QWidget):
    command_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Top Row: 4 Metric Cards
        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_ph = MetricCard("Sensor pH", "pH", "--", "#E53935")
        self.card_ec = MetricCard("Konduktivitas", "µS/cm", "--", "#FF9800")
        self.card_do = MetricCard("Dissolved Oxygen", "mg/L", "--", "#5BB5C5")
        self.card_temp = MetricCard("Suhu Air", "°C", "--", "#FF9800")

        cards_layout.addWidget(self.card_ph)
        cards_layout.addWidget(self.card_ec)
        cards_layout.addWidget(self.card_do)
        cards_layout.addWidget(self.card_temp)
        main_layout.addLayout(cards_layout)

        # 2. Main Body: Split into Left (Controls) and Right (Stability Plotter & Wizard)
        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(12)

        # Left Column: Calibration Controls
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(10)

        # --- GroupBox pH Calibration ---
        gb_ph = QtWidgets.QGroupBox("1. KALIBRASI SENSOR pH (EZO / MODULAR)")
        ph_layout = QtWidgets.QVBoxLayout(gb_ph)
        ph_layout.setSpacing(8)

        # Buttons row
        ph_btn_row = QtWidgets.QHBoxLayout()
        self.btn_ph_mid = QtWidgets.QPushButton("● Mid (7.00)")
        self.btn_ph_mid.setProperty("class", "btn-primary")
        self.btn_ph_mid.clicked.connect(lambda: self.command_requested.emit("CAL_PH,mid,7.00"))

        self.btn_ph_low = QtWidgets.QPushButton("● Low (4.00)")
        self.btn_ph_low.setProperty("class", "btn-warning")
        self.btn_ph_low.clicked.connect(lambda: self.command_requested.emit("CAL_PH,low,4.00"))

        self.btn_ph_high = QtWidgets.QPushButton("● High (10.00)")
        self.btn_ph_high.setProperty("class", "btn-primary")
        self.btn_ph_high.clicked.connect(lambda: self.command_requested.emit("CAL_PH,high,10.00"))

        ph_btn_row.addWidget(self.btn_ph_mid)
        ph_btn_row.addWidget(self.btn_ph_low)
        ph_btn_row.addWidget(self.btn_ph_high)
        ph_layout.addLayout(ph_btn_row)

        # Secondary row (Status & Clear)
        ph_sub_row = QtWidgets.QHBoxLayout()
        self.btn_ph_status = QtWidgets.QPushButton("Cek Status (?)")
        self.btn_ph_status.clicked.connect(lambda: self.command_requested.emit("CAL_PH,?"))

        self.btn_ph_clear = QtWidgets.QPushButton("Reset Pabrik")
        self.btn_ph_clear.setProperty("class", "btn-danger")
        self.btn_ph_clear.clicked.connect(lambda: self._confirm_command("CAL_PH,clear", "Yakin ingin mereset kalibrasi pH ke default?"))

        ph_sub_row.addWidget(self.btn_ph_status)
        ph_sub_row.addWidget(self.btn_ph_clear)
        ph_layout.addLayout(ph_sub_row)

        self.lbl_ph_status = QtWidgets.QLabel("Status: Siap kalibrasi")
        self.lbl_ph_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        ph_layout.addWidget(self.lbl_ph_status)
        left_col.addWidget(gb_ph)

        # --- GroupBox EC Calibration ---
        gb_ec = QtWidgets.QGroupBox("2. KALIBRASI KONDUKTIVITAS LISTRIK / EC")
        ec_layout = QtWidgets.QVBoxLayout(gb_ec)
        ec_layout.setSpacing(8)

        # Dry Calibration
        ec_row1 = QtWidgets.QHBoxLayout()
        self.btn_ec_dry = QtWidgets.QPushButton("● Kalibrasi Udara Kering (Dry)")
        self.btn_ec_dry.clicked.connect(lambda: self.command_requested.emit("CAL_EC,dry"))
        ec_row1.addWidget(self.btn_ec_dry)
        ec_layout.addLayout(ec_row1)

        # Standard 1-Point Input
        ec_row2 = QtWidgets.QHBoxLayout()
        lbl_std = QtWidgets.QLabel("Larutan Standar:")
        self.txt_ec_val = QtWidgets.QLineEdit("1413")
        self.txt_ec_val.setPlaceholderText("µS/cm")
        self.txt_ec_val.setMaximumWidth(80)

        self.btn_ec_one = QtWidgets.QPushButton("Kalibrasi 1-Point")
        self.btn_ec_one.setProperty("class", "btn-success")
        self.btn_ec_one.clicked.connect(self._on_ec_one_clicked)

        ec_row2.addWidget(lbl_std)
        ec_row2.addWidget(self.txt_ec_val)
        ec_row2.addWidget(self.btn_ec_one)
        ec_layout.addLayout(ec_row2)

        # Low & High Range
        ec_row3 = QtWidgets.QHBoxLayout()
        self.btn_ec_low = QtWidgets.QPushButton("Low (12.880)")
        self.btn_ec_low.clicked.connect(lambda: self.command_requested.emit("CAL_EC,low,12880"))
        self.btn_ec_high = QtWidgets.QPushButton("High (80.000)")
        self.btn_ec_high.clicked.connect(lambda: self.command_requested.emit("CAL_EC,high,80000"))
        self.btn_ec_status = QtWidgets.QPushButton("Cek Status (?)")
        self.btn_ec_status.clicked.connect(lambda: self.command_requested.emit("CAL_EC,?"))
        self.btn_ec_clear = QtWidgets.QPushButton("Reset")
        self.btn_ec_clear.setProperty("class", "btn-danger")
        self.btn_ec_clear.clicked.connect(lambda: self._confirm_command("CAL_EC,clear", "Yakin ingin mereset kalibrasi EC ke default?"))

        ec_row3.addWidget(self.btn_ec_low)
        ec_row3.addWidget(self.btn_ec_high)
        ec_row3.addWidget(self.btn_ec_status)
        ec_row3.addWidget(self.btn_ec_clear)
        ec_layout.addLayout(ec_row3)

        self.lbl_ec_status = QtWidgets.QLabel("Status: Siap kalibrasi")
        self.lbl_ec_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        ec_layout.addWidget(self.lbl_ec_status)
        left_col.addWidget(gb_ec)

        # --- GroupBox Dissolved Oxygen Calibration ---
        gb_do = QtWidgets.QGroupBox("3. KALIBRASI DISSOLVED OXYGEN / DO")
        do_layout = QtWidgets.QVBoxLayout(gb_do)
        do_layout.setSpacing(8)

        do_btn_row = QtWidgets.QHBoxLayout()
        self.btn_do_sat = QtWidgets.QPushButton("● 100% Saturation (Air Cal)")
        self.btn_do_sat.setProperty("class", "btn-success")
        self.btn_do_sat.clicked.connect(lambda: self.command_requested.emit("CAL_DO,sat,100"))

        self.btn_do_zero = QtWidgets.QPushButton("● 0% Zero DO (Na2SO3)")
        self.btn_do_zero.setProperty("class", "btn-warning")
        self.btn_do_zero.clicked.connect(lambda: self.command_requested.emit("CAL_DO,zero"))

        self.btn_do_clear = QtWidgets.QPushButton("Reset")
        self.btn_do_clear.setProperty("class", "btn-danger")
        self.btn_do_clear.clicked.connect(lambda: self._confirm_command("CAL_DO,clear", "Reset kalibrasi DO?"))

        do_btn_row.addWidget(self.btn_do_sat)
        do_btn_row.addWidget(self.btn_do_zero)
        do_btn_row.addWidget(self.btn_do_clear)
        do_layout.addLayout(do_btn_row)

        self.lbl_do_status = QtWidgets.QLabel("Status: Siap kalibrasi")
        self.lbl_do_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        do_layout.addWidget(self.lbl_do_status)
        left_col.addWidget(gb_do)

        # --- GroupBox Temperature Calibration (Atlas Surveyor RTD PT-1000) ---
        gb_temp = QtWidgets.QGroupBox("4. KALIBRASI SUHU (ATLAS SURVEYOR™ RTD PT-1000)")
        temp_layout = QtWidgets.QVBoxLayout(gb_temp)
        temp_layout.setSpacing(8)

        # Row 1: Ice Bath 0°C Quick Calibrate
        temp_row1 = QtWidgets.QHBoxLayout()
        self.btn_temp_ice = QtWidgets.QPushButton("● Ice Bath (0.0 °C)")
        self.btn_temp_ice.setObjectName("btn_temp_ice")
        self.btn_temp_ice.clicked.connect(lambda: self.command_requested.emit("CAL_TEMP,ice,0.0"))
        temp_row1.addWidget(self.btn_temp_ice)
        temp_layout.addLayout(temp_row1)

        # Row 2: Standard Reference Point
        temp_row2 = QtWidgets.QHBoxLayout()
        lbl_std_temp = QtWidgets.QLabel("Suhu Acuan:")
        self.txt_temp_val = QtWidgets.QLineEdit("25.0")
        self.txt_temp_val.setPlaceholderText("°C")
        self.txt_temp_val.setMaximumWidth(70)

        self.btn_temp_one = QtWidgets.QPushButton("Kalibrasi 1-Point")
        self.btn_temp_one.setObjectName("btn_temp_custom")
        self.btn_temp_one.clicked.connect(self._on_temp_one_clicked)

        temp_row2.addWidget(lbl_std_temp)
        temp_row2.addWidget(self.txt_temp_val)
        temp_row2.addWidget(self.btn_temp_one)
        temp_layout.addLayout(temp_row2)

        # Row 3: Status & Reset
        temp_row3 = QtWidgets.QHBoxLayout()
        self.btn_temp_status = QtWidgets.QPushButton("Cek Status (?)")
        self.btn_temp_status.clicked.connect(lambda: self.command_requested.emit("CAL_TEMP,?"))

        self.btn_temp_clear = QtWidgets.QPushButton("Reset Pabrik")
        self.btn_temp_clear.setObjectName("btn_temp_clear")
        self.btn_temp_clear.clicked.connect(lambda: self._confirm_command(
            "CAL_TEMP,clear", "Reset kalibrasi suhu ke default pabrik (1.058V, 9mV/°C)?"
        ))

        temp_row3.addWidget(self.btn_temp_status)
        temp_row3.addWidget(self.btn_temp_clear)
        temp_layout.addLayout(temp_row3)

        self.lbl_temp_status = QtWidgets.QLabel("Status: Siap kalibrasi suhu")
        self.lbl_temp_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        temp_layout.addWidget(self.lbl_temp_status)
        left_col.addWidget(gb_temp)

        body_layout.addLayout(left_col, stretch=4)

        # Right Column: Stability Plotter & Step Wizard
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(10)

        # Stability Plotter
        self.plotter = StabilityPlotterWidget("PEMANTAUAN KESTABILAN KUALITAS AIR")
        right_col.addWidget(self.plotter, stretch=6)

        # Step Guide / Wizard Box
        gb_guide = QtWidgets.QGroupBox("PANDUAN PROSEDUR KALIBRASI KIMIA AIR")
        guide_layout = QtWidgets.QVBoxLayout(gb_guide)
        guide_text = QtWidgets.QLabel(
            "<b>Langkah Prosedur yang Disarankan:</b><br>"
            "1. <b>Bilas Probe:</b> Gunakan air akuades/demineralisasi dan lap lembut dengan tisu bebas serat.<br>"
            "2. <b>Celupkan Probe:</b> Pastikan bagian kaca/elektroda terendam sempurna di larutan buffer.<br>"
            "3. <b>Pantau Grafik Kestabilan:</b> Tunggu hingga badge berubah menjadi <b>[STABIL]</b> (StdDev &lt; 0.03).<br>"
            "4. <b>Tekan Tombol Kalibrasi:</b> Untuk pH, selalu mulai dari <b>Mid (pH 7.00)</b> terlebih dahulu baru Low/High.<br>"
            "5. <b>Suhu (Atlas RTD):</b> Buat bubur es batu 75% + 25% air dingin (0.0 °C). Tunggu stabil lalu klik <b>[Ice Bath (0.0 °C)]</b>."
        )
        guide_text.setStyleSheet("color: #CCCCCC; font-size: 11px; line-height: 140%;")
        guide_layout.addWidget(guide_text)
        right_col.addWidget(gb_guide, stretch=3)

        body_layout.addLayout(right_col, stretch=6)
        main_layout.addLayout(body_layout)

    def _on_ec_one_clicked(self):
        val = self.txt_ec_val.text().strip()
        if not val:
            val = "1413"
        self.command_requested.emit(f"CAL_EC,one,{val}")

    def _on_temp_one_clicked(self):
        val = self.txt_temp_val.text().strip()
        if not val:
            val = "25.0"
        self.command_requested.emit(f"CAL_TEMP,cal,{val}")

    def _confirm_command(self, cmd: str, message: str):
        reply = QtWidgets.QMessageBox.question(
            self, "Konfirmasi Kalibrasi", message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.command_requested.emit(cmd)

    def update_telemetry(self, data: dict):
        # Update Metric Cards
        ph = data.get("ph", 0.0)
        ec = data.get("ec", 0.0)
        do = data.get("do", 0.0)
        temp = data.get("temp", 0.0)

        self.card_ph.set_value(f"{ph:.2f}")
        self.card_ec.set_value(f"{ec:.0f}")
        self.card_do.set_value(f"{do:.2f}")
        self.card_temp.set_value(f"{temp:.1f}")

        # Update Plotter
        self.plotter.add_telemetry(data)

    def handle_cal_response(self, sensor: str, resp: str):
        if sensor == "PH":
            self.lbl_ph_status.setText(f"Status: {resp}")
            self.lbl_ph_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "EC":
            self.lbl_ec_status.setText(f"Status: {resp}")
            self.lbl_ec_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "DO":
            self.lbl_do_status.setText(f"Status: {resp}")
            self.lbl_do_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "TEMP":
            self.lbl_temp_status.setText(f"Status: {resp}")
            self.lbl_temp_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
