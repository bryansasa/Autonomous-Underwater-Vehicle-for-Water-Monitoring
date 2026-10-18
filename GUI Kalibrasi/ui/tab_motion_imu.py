# -*- coding: utf-8 -*-
"""
Tab 2: Robot Motion & Orientation Calibration (Charisto's Components)
Supports:
- IMU Gyroscope Zero-Rate Bias
- IMU Accelerometer / Horizon Leveling Tare
- Magnetometer Hard/Soft-Iron Calibration with Interactive 2D Scatter Fitting
- Depth / Pressure Sensor Surface Tare & Fluid Density Configuration
"""

import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore, QtGui
from core.cal_engine import MagnetometerFitter, GyroBiasAccumulator
from ui.widgets.metric_card import MetricCard


class MotionIMUTab(QtWidgets.QWidget):
    command_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mag_fitter = MagnetometerFitter()
        self.gyro_acc = GyroBiasAccumulator(target_samples=100)
        self.is_mag_streaming = False
        self.is_gyro_calibrating = False

        self._init_ui()

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Top Row: 5 Metric Cards
        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(8)

        self.card_roll = MetricCard("Roll", "°", "--", "#E53935")
        self.card_pitch = MetricCard("Pitch", "°", "--", "#FF9800")
        self.card_yaw = MetricCard("Heading (Yaw)", "°", "--", "#5BB5C5")
        self.card_depth = MetricCard("Kedalaman Z", "m", "--", "#E53935")
        self.card_press = MetricCard("Tekanan", "mbar", "--", "#FF9800")

        cards_layout.addWidget(self.card_roll)
        cards_layout.addWidget(self.card_pitch)
        cards_layout.addWidget(self.card_yaw)
        cards_layout.addWidget(self.card_depth)
        cards_layout.addWidget(self.card_press)
        main_layout.addLayout(cards_layout)

        # 2. Body Layout: Left (Gyro, Level, Depth) vs Right (Magnetometer 2D Plot)
        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(12)

        # Left Column: Gyro, Level, Depth
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(10)

        # --- Gyro Zero-Rate Bias ---
        gb_gyro = QtWidgets.QGroupBox("1. GYROSCOPE ZERO-RATE BIAS")
        gyro_layout = QtWidgets.QVBoxLayout(gb_gyro)
        gyro_layout.setSpacing(6)

        self.btn_gyro_cal = QtWidgets.QPushButton("● Mulai Kalibrasi Gyro (Wahana Diam)")
        self.btn_gyro_cal.setProperty("class", "btn-primary")
        self.btn_gyro_cal.clicked.connect(self._start_gyro_cal)

        self.bar_gyro = QtWidgets.QProgressBar()
        self.bar_gyro.setValue(0)

        self.lbl_gyro_status = QtWidgets.QLabel("Status: Letakkan wahana pada permukaan stabil tanpa getaran.")
        self.lbl_gyro_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")

        gyro_layout.addWidget(self.btn_gyro_cal)
        gyro_layout.addWidget(self.bar_gyro)
        gyro_layout.addWidget(self.lbl_gyro_status)
        left_col.addWidget(gb_gyro)

        # --- Horizon Leveling Tare ---
        gb_level = QtWidgets.QGroupBox("2. HORIZON LEVELING TARE (ROLL & PITCH)")
        level_layout = QtWidgets.QVBoxLayout(gb_level)
        level_layout.setSpacing(6)

        self.btn_level_tare = QtWidgets.QPushButton("● Tare Horizon (Set Roll & Pitch = 0.0°)")
        self.btn_level_tare.setProperty("class", "btn-success")
        self.btn_level_tare.clicked.connect(lambda: self.command_requested.emit("CAL_IMU,level"))

        self.lbl_level_status = QtWidgets.QLabel("Status: Posisikan robot datar sebelum menekan tare.")
        self.lbl_level_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")

        level_layout.addWidget(self.btn_level_tare)
        level_layout.addWidget(self.lbl_level_status)
        left_col.addWidget(gb_level)

        # --- Depth & Pressure Sensor ---
        gb_depth = QtWidgets.QGroupBox("3. SENSOR KEDALAMAN (MS5837 / BAR30)")
        depth_layout = QtWidgets.QVBoxLayout(gb_depth)
        depth_layout.setSpacing(8)

        # Surface Zero Tare
        self.btn_depth_tare = QtWidgets.QPushButton("● Tare Permukaan Air (Z = 0.00 m)")
        self.btn_depth_tare.setProperty("class", "btn-warning")
        self.btn_depth_tare.clicked.connect(lambda: self.command_requested.emit("CAL_DEPTH,tare"))
        depth_layout.addWidget(self.btn_depth_tare)

        # Water Density Config
        density_row = QtWidgets.QHBoxLayout()
        lbl_dens = QtWidgets.QLabel("Densitas Fluida:")
        self.txt_density = QtWidgets.QLineEdit("997.0")
        self.txt_density.setMaximumWidth(70)
        lbl_unit = QtWidgets.QLabel("kg/m³ (Waduk Saguling)")
        lbl_unit.setStyleSheet("color: #CCCCCC; font-size: 11px;")

        self.btn_set_density = QtWidgets.QPushButton("Set")
        self.btn_set_density.clicked.connect(self._on_set_density)

        density_row.addWidget(lbl_dens)
        density_row.addWidget(self.txt_density)
        density_row.addWidget(lbl_unit)
        density_row.addWidget(self.btn_set_density)
        depth_layout.addLayout(density_row)

        self.lbl_depth_status = QtWidgets.QLabel("Status: Tekan tare saat robot mengapung di permukaan air.")
        self.lbl_depth_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        depth_layout.addWidget(self.lbl_depth_status)

        left_col.addWidget(gb_depth)
        body_layout.addLayout(left_col, stretch=4)

        # Right Column: Magnetometer Calibration Plot
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(10)

        gb_mag = QtWidgets.QGroupBox("4. KALIBRASI MAGNETOMETER / KOMPAS (HARD & SOFT IRON)")
        mag_layout = QtWidgets.QVBoxLayout(gb_mag)
        mag_layout.setSpacing(8)

        # Plot Widget
        self.plot_mag = pg.PlotWidget()
        self.plot_mag.setBackground("#181818")
        self.plot_mag.showGrid(x=True, y=True, alpha=0.3)
        self.plot_mag.setLabel("bottom", "Bx (Medan Magnet Sumbu X)")
        self.plot_mag.setLabel("left", "By (Medan Magnet Sumbu Y)")
        self.plot_mag.setAspectLocked(True)

        # Scatter item for raw points
        self.scatter_raw = pg.ScatterPlotItem(size=6, pen=pg.mkPen(None), brush=pg.mkBrush(229, 57, 53, 180))
        self.plot_mag.addItem(self.scatter_raw)

        # Ellipse / Circle curve for fitted model
        self.curve_fit = self.plot_mag.plot(pen=pg.mkPen(color="#E53935", width=2, style=QtCore.Qt.DashLine))
        mag_layout.addWidget(self.plot_mag, stretch=5)

        # Controls Row
        mag_ctrl_row = QtWidgets.QHBoxLayout()
        self.btn_mag_stream = QtWidgets.QPushButton("● Mulai Putar 360°")
        self.btn_mag_stream.setProperty("class", "btn-primary")
        self.btn_mag_stream.clicked.connect(self._toggle_mag_stream)

        self.btn_mag_fit = QtWidgets.QPushButton("Kalkulasi Fitting")
        self.btn_mag_fit.clicked.connect(self._fit_magnetometer)

        self.btn_mag_save = QtWidgets.QPushButton("Simpan ke EEPROM")
        self.btn_mag_save.setProperty("class", "btn-success")
        self.btn_mag_save.clicked.connect(lambda: self.command_requested.emit("CAL_MAG,save"))

        self.btn_mag_clear = QtWidgets.QPushButton("Hapus Data")
        self.btn_mag_clear.clicked.connect(self._clear_mag_plot)

        mag_ctrl_row.addWidget(self.btn_mag_stream)
        mag_ctrl_row.addWidget(self.btn_mag_fit)
        mag_ctrl_row.addWidget(self.btn_mag_save)
        mag_ctrl_row.addWidget(self.btn_mag_clear)
        mag_layout.addLayout(mag_ctrl_row)

        self.lbl_mag_status = QtWidgets.QLabel(
            "Panduan: Klik 'Mulai Putar 360°', gerakkan robot memutar dan bentuk angka 8, lalu klik 'Kalkulasi Fitting'."
        )
        self.lbl_mag_status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        mag_layout.addWidget(self.lbl_mag_status)

        right_col.addWidget(gb_mag, stretch=6)
        body_layout.addLayout(right_col, stretch=6)
        main_layout.addLayout(body_layout)

    # --- Gyro Calibration Logic ---
    def _start_gyro_cal(self):
        self.gyro_acc.clear()
        self.is_gyro_calibrating = True
        self.bar_gyro.setValue(0)
        self.lbl_gyro_status.setText("Sedang mengumpulkan 100 sampel diam...")
        self.lbl_gyro_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")

    # --- Density Logic ---
    def _on_set_density(self):
        val = self.txt_density.text().strip()
        try:
            d_val = float(val)
            self.command_requested.emit(f"CAL_DEPTH,density,{d_val:.1f}")
        except ValueError:
            self.lbl_depth_status.setText("ERROR: Nilai densitas tidak valid.")

    # --- Magnetometer Logic ---
    def _toggle_mag_stream(self):
        if not self.is_mag_streaming:
            self.is_mag_streaming = True
            self.btn_mag_stream.setText("■ Berhenti Putar")
            self.btn_mag_stream.setProperty("class", "btn-warning")
            self.lbl_mag_status.setText("Menerima titik koordinat (Bx, By)... Putar wahana perlahan.")
            self.command_requested.emit("CAL_MAG,start")
        else:
            self.is_mag_streaming = False
            self.btn_mag_stream.setText("● Mulai Putar 360°")
            self.btn_mag_stream.setProperty("class", "btn-primary")
            self.command_requested.emit("CAL_MAG,stop")

    def _clear_mag_plot(self):
        self.mag_fitter.clear()
        self.scatter_raw.clear()
        self.curve_fit.clear()
        self.lbl_mag_status.setText("Data magnetometer dibersihkan.")

    def _fit_magnetometer(self):
        res = self.mag_fitter.fit_2d()
        if not res["valid"]:
            self.lbl_mag_status.setText(f"Gagal: {res.get('msg', 'Data tidak cukup')}")
            self.lbl_mag_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
            return

        ox = res["center_x"]
        oy = res["center_y"]
        r = res["radius"]
        rms = res["rms_error"]

        # Draw fitted circle
        import numpy as np
        theta = np.linspace(0, 2 * np.pi, 100)
        cx = ox + r * np.cos(theta)
        cy = oy + r * np.sin(theta)
        self.curve_fit.setData(cx, cy)

        self.lbl_mag_status.setText(
            f"Fitting Sukses: Offset Pusat=({ox:.1f}, {oy:.1f}) | Radius R={r:.1f} | RMS Galat={rms:.2f}"
        )
        self.lbl_mag_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")

    def add_mag_sample(self, bx: float, by: float, bz: float):
        self.mag_fitter.add_sample(bx, by, bz)
        self.scatter_raw.addPoints([{'pos': (bx, by)}])

    def update_telemetry(self, data: dict):
        roll = data.get("roll", 0.0)
        pitch = data.get("pitch", 0.0)
        yaw = data.get("yaw", 0.0)
        depth = data.get("depth", 0.0)
        press = data.get("press", 1013.25)

        self.card_roll.set_value(f"{roll:+.1f}")
        self.card_pitch.set_value(f"{pitch:+.1f}")
        self.card_yaw.set_value(f"{yaw:.1f}")
        self.card_depth.set_value(f"{depth:.3f}")
        self.card_press.set_value(f"{press:.1f}")

        # Color-code roll & pitch if unlevel
        if abs(roll) > 5.0 or abs(pitch) > 5.0:
            self.card_roll.set_status("● Miring / Trim", "#FF9800")
        else:
            self.card_roll.set_status("● Level Datar", "#E53935")

        # Gyro sampling accumulation
        if self.is_gyro_calibrating:
            self.gyro_acc.add_sample(roll, pitch, yaw)
            pct = int(self.gyro_acc.progress_pct())
            self.bar_gyro.setValue(pct)
            if self.gyro_acc.is_complete():
                self.is_gyro_calibrating = False
                res = self.gyro_acc.calculate_bias()
                self.lbl_gyro_status.setText(
                    f"Kalibrasi Selesai: Bias dihitung dari {res['samples']} sampel."
                )
                self.lbl_gyro_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
                self.command_requested.emit("CAL_IMU,gyro")

    def handle_cal_response(self, sensor: str, resp: str):
        if sensor == "IMU":
            self.lbl_level_status.setText(f"Status: {resp}")
            self.lbl_level_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "MAG":
            self.lbl_mag_status.setText(f"Status: {resp}")
            self.lbl_mag_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        elif sensor == "DEPTH":
            self.lbl_depth_status.setText(f"Status: {resp}")
            self.lbl_depth_status.setStyleSheet("color: #FFFFFF; font-weight: bold;")
