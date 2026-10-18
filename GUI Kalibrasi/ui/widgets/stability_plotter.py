# -*- coding: utf-8 -*-
"""
Real-time Sensor Stability Plotter Widget
Minimalist Industrial Matte Dark with Red Accent.
"""

import collections
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from core.cal_engine import StabilityDetector


class StabilityPlotterWidget(QtWidgets.QFrame):
    def __init__(self, title: str = "PEMANTAUAN KESTABILAN SINYAL REAL-TIME", parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("""
            StabilityPlotterWidget {
                background-color: #222222;
                border: 1px solid #333333;
                border-radius: 4px;
            }
        """)

        # Rolling buffers
        self.max_points = 250
        self.data_x = collections.deque(maxlen=self.max_points)
        self.data_y = collections.deque(maxlen=self.max_points)
        self.time_counter = 0

        # Stability detector
        self.detector = StabilityDetector(window_size=30, std_threshold=0.03)

        self._init_ui(title)

    def _init_ui(self, title: str):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header bar
        header_layout = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 11px;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        # Selector for sensor stream
        lbl_sel = QtWidgets.QLabel("Kanal:")
        lbl_sel.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        self.combo_channel = QtWidgets.QComboBox()
        self.combo_channel.addItems(["pH", "EC (uS/cm)", "DO (mg/L)", "Suhu (°C)", "Roll (°)", "Pitch (°)", "Kedalaman (m)"])
        self.combo_channel.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.combo_channel.currentIndexChanged.connect(self._on_channel_changed)
        header_layout.addWidget(lbl_sel)
        header_layout.addWidget(self.combo_channel)

        # Stability Badge
        self.lbl_badge = QtWidgets.QLabel("● MENUNGGU DATA")
        self.lbl_badge.setStyleSheet("""
            background-color: #181818;
            color: #9E9E9E;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.lbl_badge)
        layout.addLayout(header_layout)

        # PyQtGraph Plot Widget
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#181818")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setMouseEnabled(x=False, y=True)
        self.plot_widget.getAxis("bottom").setTextPen(pg.mkPen(color="#9E9E9E"))
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen(color="#9E9E9E"))

        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color="#E53935", width=2),
            brush=pg.mkBrush(color=(229, 57, 53, 30)),
            fillLevel=0.0
        )
        layout.addWidget(self.plot_widget)

    def _on_channel_changed(self, idx: int):
        self.data_x.clear()
        self.data_y.clear()
        self.time_counter = 0
        self.detector.clear()

        # Update threshold per channel
        ch_text = self.combo_channel.currentText()
        if "pH" in ch_text:
            self.detector.std_threshold = 0.03
            self.curve.setPen(pg.mkPen(color="#E53935", width=2))
        elif "EC" in ch_text:
            self.detector.std_threshold = 3.0
            self.curve.setPen(pg.mkPen(color="#FF9800", width=2))
        elif "DO" in ch_text:
            self.detector.std_threshold = 0.05
            self.curve.setPen(pg.mkPen(color="#5BB5C5", width=2))
        elif "Suhu" in ch_text:
            self.detector.std_threshold = 0.05
            self.curve.setPen(pg.mkPen(color="#FF9800", width=2))
        elif "Kedalaman" in ch_text:
            self.detector.std_threshold = 0.01
            self.curve.setPen(pg.mkPen(color="#4A90D9", width=2))
        else:
            self.detector.std_threshold = 0.15
            self.curve.setPen(pg.mkPen(color="#E53935", width=2))

    def add_telemetry(self, telemetry: dict):
        ch = self.combo_channel.currentIndex()
        # Mapping: 0: pH, 1: EC, 2: DO, 3: Temp, 4: Roll, 5: Pitch, 6: Depth
        keys = ["ph", "ec", "do", "temp", "roll", "pitch", "depth"]
        chosen_key = keys[ch] if ch < len(keys) else "ph"

        val = float(telemetry.get(chosen_key, 0.0))
        self.time_counter += 1

        self.data_x.append(self.time_counter)
        self.data_y.append(val)
        self.detector.add_sample(val)

        # Update plot line
        self.curve.setData(list(self.data_x), list(self.data_y))

        # Update stability badge
        stats = self.detector.get_stats()
        if not stats["ready"]:
            self.lbl_badge.setText("● MENGUMPULKAN DATA...")
            self.lbl_badge.setStyleSheet("""
                background-color: #181818;
                color: #9E9E9E;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
        elif stats["is_stable"]:
            self.lbl_badge.setText(f"● STABIL / SIAP KALIBRASI (σ={stats['std']:.3f} | Δ={stats['p2p']:.3f})")
            self.lbl_badge.setStyleSheet("""
                background-color: rgba(229, 57, 53, 0.18);
                color: #FFFFFF;
                border: 1px solid #E53935;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.lbl_badge.setText(f"● FLUKTUATIF / MENUNGGU (σ={stats['std']:.3f} | Δ={stats['p2p']:.3f})")
            self.lbl_badge.setStyleSheet("""
                background-color: rgba(255, 152, 0, 0.18);
                color: #FFFFFF;
                border: 1px solid #F57C00;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
