# -*- coding: utf-8 -*-
"""
Sensor Graph Tab (Tab 2)
Clean, professional 3-color palette for real-time oscilloscope slots:
  1. Blue (#4A90D9) for Primary Metrics (Depth, pH, DO, Cond)
  2. Red & Amber for Adaptive/Filtered Signals (TBM, Kalman Batt)
  3. Amber (#EA4335) for Raw Unfiltered Signals & Tracking Errors
"""
from typing import Dict, Any, List
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore, QtGui

pg.setConfigOption('background', '#1A1D23')
pg.setConfigOption('foreground', '#9AA0A6')
pg.setConfigOption('antialias', True)


class SensorGraphTab(QtWidgets.QWidget):
    """
    Dynamic 4-Slot Sensor Graph Visualizer with a cohesive 3-color palette.
    """

    CHANNELS = {
        # Core Parameters (Professional Blue #4A90D9)
        "PH": {"name": "pH Level (Adaptive)", "color": "#4A90D9", "field": "ph"},
        "CONDUCTIVITY": {"name": "Conductivity (µS/cm)", "color": "#4A90D9", "field": "cond"},
        "DISSOLVED OXYGEN": {"name": "Dissolved Oxygen (mg/L)", "color": "#4A90D9", "field": "do"},
        "TEMPERATURE": {"name": "Temperature (°C)", "color": "#4A90D9", "field": "temp"},
        "DEPTH": {"name": "Depth (m)", "color": "#4A90D9", "field": "depth"},
        "CURRENT": {"name": "Current Draw (A)", "color": "#4A90D9", "field": "current_a"},

        # Secondary / Status / Interval Metrics (Red, Amber & Purple)
        "BATTERY": {"name": "Battery Thruster (6S, V)", "color": "#E53935", "field": "battery_v"},
        "BATT_SENSOR": {"name": "Battery Sensor (3S/Rail, V)", "color": "#AB47BC", "field": "sensor_battery_v"},
        "CURRENT_SENSOR": {"name": "Current Sensor Rail (A)", "color": "#26A69A", "field": "sensor_current_a"},
        "TBM_TEMP": {"name": "TBM Temp (s)", "color": "#FF9800", "field": "tbm_temp"},
        "TBM_PH": {"name": "TBM pH (s)", "color": "#FF9800", "field": "tbm_ph"},
        "TBM_DO": {"name": "TBM DO (s)", "color": "#FF9800", "field": "tbm_do"},
        "TBM_COND": {"name": "TBM Cond (s)", "color": "#FF9800", "field": "tbm_cond"},

        # Error & Raw Signals (Google Red #EA4335)
        "ERROR DEPTH": {"name": "LMPC Tracking Error (m)", "color": "#EA4335", "field": "error_depth"},
        "RAW_TEMP": {"name": "Raw Temperature (°C)", "color": "#EA4335", "field": "raw_temp"},
        "RAW_PH": {"name": "Raw pH", "color": "#EA4335", "field": "raw_ph"},
        "RAW_DO": {"name": "Raw DO (mg/L)", "color": "#EA4335", "field": "raw_do"},
        "RAW_COND": {"name": "Raw Conductivity (µS/cm)", "color": "#EA4335", "field": "raw_cond"},
        "RAW_PRESSURE": {"name": "Raw Pressure (mbar)", "color": "#EA4335", "field": "raw_pressure"}
    }

    def __init__(self, max_points: int = 150, parent=None):
        super().__init__(parent)
        self.max_points = max_points
        self.active_slots = [None, None, None, None]  # 4 slots
        self.buffers: Dict[str, List[float]] = {k: [] for k in self.CHANNELS.keys()}
        self.checkboxes: Dict[str, QtWidgets.QCheckBox] = {}

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. Top Checkboxes Selector Frame
        self.cb_frame = QtWidgets.QFrame()
        self.cb_frame.setObjectName("hudCard")
        cb_grid = QtWidgets.QGridLayout(self.cb_frame)
        cb_grid.setContentsMargins(8, 6, 8, 6)
        cb_grid.setSpacing(4)

        # Row 0: Adaptive Water Quality & Navigation
        row0_keys = ["PH", "DISSOLVED OXYGEN", "DEPTH", "CURRENT", "TBM_TEMP", "TBM_DO", "RAW_TEMP", "RAW_DO"]
        for col, k in enumerate(row0_keys):
            cb = QtWidgets.QCheckBox(k)
            cb.setStyleSheet("font-size: 11px; font-weight: 600; color: #D2D4D7;")
            cb.toggled.connect(lambda chk, key=k: self.on_checkbox_toggled(key, chk))
            self.checkboxes[k] = cb
            cb_grid.addWidget(cb, 0, col)

        # Row 1: Adaptive Cond/Temp & Other Parameters
        row1_keys = ["CONDUCTIVITY", "TEMPERATURE", "ERROR DEPTH", "BATTERY", "TBM_PH", "TBM_COND", "RAW_PH", "RAW_COND"]
        for col, k in enumerate(row1_keys):
            cb = QtWidgets.QCheckBox(k)
            cb.setStyleSheet("font-size: 11px; font-weight: 600; color: #D2D4D7;")
            cb.toggled.connect(lambda chk, key=k: self.on_checkbox_toggled(key, chk))
            self.checkboxes[k] = cb
            cb_grid.addWidget(cb, 1, col)

        # Row 2: Secondary Power Rail (Sensor & MCU)
        row2_keys = ["BATT_SENSOR", "CURRENT_SENSOR"]
        for col, k in enumerate(row2_keys):
            cb = QtWidgets.QCheckBox(k)
            cb.setStyleSheet("font-size: 11px; font-weight: 600; color: #D2D4D7;")
            cb.toggled.connect(lambda chk, key=k: self.on_checkbox_toggled(key, chk))
            self.checkboxes[k] = cb
            cb_grid.addWidget(cb, 2, col)

        main_layout.addWidget(self.cb_frame)

        # 2. 2x2 Graphics Layout for 4 Slots
        self.gl_widget = pg.GraphicsLayoutWidget()
        self.gl_widget.setBackground("#1A1D23")

        # Create 4 Plot Items
        self.plots = []
        self.curves = []

        coords = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for idx, (r, c) in enumerate(coords):
            p = self.gl_widget.addPlot(row=r, col=c, title=f"<b style='color:#9AA0A6'>SLOT {idx+1}: (KOSONG)</b>")
            p.showGrid(x=True, y=True, alpha=0.3)
            curve = p.plot(pen=pg.mkPen('#4A90D9', width=2))
            self.plots.append(p)
            self.curves.append(curve)

        main_layout.addWidget(self.gl_widget, stretch=1)

        # Default activate first 4
        defaults = ["PH", "DISSOLVED OXYGEN", "DEPTH", "CONDUCTIVITY"]
        for k in defaults:
            if k in self.checkboxes:
                self.checkboxes[k].setChecked(True)

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name
        text_clr = "#D2D4D7" if is_dark else "#0F172A"
        for cb in self.checkboxes.values():
            cb.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {text_clr};")

        bg_clr = "#1A1D23" if is_dark else "#FFFFFF"
        self.gl_widget.setBackground(bg_clr)

        title_clr = "#9AA0A6" if is_dark else "#334155"
        axis_pen = pg.mkPen(color=title_clr, width=1)
        for i, p in enumerate(self.plots):
            p.getAxis('bottom').setPen(axis_pen)
            p.getAxis('left').setPen(axis_pen)
            p.getAxis('bottom').setTextPen(axis_pen)
            p.getAxis('left').setTextPen(axis_pen)
            if self.active_slots[i] is None:
                p.setTitle(f"<b style='color:{title_clr}'>SLOT {i+1}: (KOSONG)</b>")
            else:
                meta = self.CHANNELS[self.active_slots[i]]
                p.setTitle(f"<b style='color:{meta['color']}'>{meta['name']}</b>")

    def on_checkbox_toggled(self, key: str, checked: bool):
        if checked:
            # Find first available slot
            assigned = False
            for i in range(4):
                if self.active_slots[i] is None:
                    self.active_slots[i] = key
                    meta = self.CHANNELS[key]
                    self.plots[i].setTitle(f"<b style='color:{meta['color']}'>{meta['name']}</b>")
                    self.curves[i].setPen(pg.mkPen(meta['color'], width=2))
                    assigned = True
                    break
            if not assigned:
                self.checkboxes[key].blockSignals(True)
                self.checkboxes[key].setChecked(False)
                self.checkboxes[key].blockSignals(False)
                QtWidgets.QMessageBox.information(
                    self, "Batas Grafik", "Maksimal 4 grafik dapat ditampilkan secara bersamaan.\nHapus centang salah satu slot terlebih dahulu."
                )
        else:
            # Remove from slot
            for i in range(4):
                if self.active_slots[i] == key:
                    self.active_slots[i] = None
                    self.plots[i].setTitle(f"<b style='color:#9AA0A6'>SLOT {i+1}: (KOSONG)</b>")
                    self.curves[i].setData([])
                    break

    def add_telemetry(self, data: Dict[str, Any]):
        # Populate all buffers
        for key, meta in self.CHANNELS.items():
            field = meta["field"]
            val = data.get(field, 0.0)
            self.buffers[key].append(float(val))
            if len(self.buffers[key]) > self.max_points:
                self.buffers[key].pop(0)

        # Update active curves
        for i in range(4):
            key = self.active_slots[i]
            if key and key in self.buffers:
                self.curves[i].setData(self.buffers[key])
