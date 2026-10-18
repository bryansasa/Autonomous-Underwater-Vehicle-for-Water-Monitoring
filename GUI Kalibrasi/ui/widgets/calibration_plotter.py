# -*- coding: utf-8 -*-
"""
Real-time Interactive Calibration Plotter Widget for Sensor Calibration Suite
Features:
- Live streaming synchronized with incoming telemetry packets
- Dynamic auto-adjust & auto-fit scaling with smart padding
- Full interactive zoom (mouse wheel, box zoom, zoom in/out buttons, drag pan)
- Stream Pause/Resume to freeze view and inspect data points comfortably
- Interactive Crosshair with nearest-point snapping & highlighted scatter marker
- Precise timestamp readout (YYYY-MM-DD HH:MM:SS.zzz & relative elapsed time)
- Signal stability detection & real-time rolling statistics (StdDev, Mean, P2P)
- Channel selector defaulting to Conductivity (EC)
"""

import time
from datetime import datetime
from collections import deque
import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from core.cal_engine import StabilityDetector


class CalibrationPlotterWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setObjectName("calPlotterFrame")

        # Configuration & Channel definitions
        self.channels = {
            "EC": {
                "name": "Konduktivitas (EC)",
                "key": "ec",
                "unit": "µS/cm",
                "color": "#FF9800",       # Vibrant Amber
                "threshold": 3.0,
                "window": 25,
                "format": "{:.1f}"
            },
            "PH": {
                "name": "Sensor pH",
                "key": "ph",
                "unit": "pH",
                "color": "#E53935",       # Bright Red
                "threshold": 0.03,
                "window": 25,
                "format": "{:.2f}"
            },
            "DO": {
                "name": "Dissolved Oxygen (DO)",
                "key": "do",
                "unit": "mg/L",
                "color": "#00BCD4",       # Cyan
                "threshold": 0.05,
                "window": 25,
                "format": "{:.2f}"
            },
            "TEMP": {
                "name": "Suhu Air (Atlas RTD PT-1000)",
                "key": "temp",
                "unit": "°C",
                "color": "#4CAF50",       # Green
                "threshold": 0.05,
                "window": 25,
                "format": "{:.2f}"
            },
            "DEPTH": {
                "name": "Kedalaman (Depth)",
                "key": "depth",
                "unit": "m",
                "color": "#2196F3",       # Blue
                "threshold": 0.01,
                "window": 25,
                "format": "{:.3f}"
            }
        }

        self.current_channel_key = "EC"
        self.max_buffer_points = 500

        # Data buffers
        self.buffer_timestamps = deque(maxlen=self.max_buffer_points)   # datetime objects
        self.buffer_time_floats = deque(maxlen=self.max_buffer_points)  # elapsed seconds from first point
        self.buffer_values = deque(maxlen=self.max_buffer_points)       # sensor values
        self.buffer_teensy_ms = deque(maxlen=self.max_buffer_points)    # raw teensy ms
        self.sample_counter = 0
        self.first_time_epoch = None

        # State flags
        self.is_paused = False
        self.auto_scroll = True

        # Stability detector
        self.detector = StabilityDetector(window_size=25, std_threshold=3.0)

        # Build UI
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. TOP TOOLBAR: Channel Selector + Stability Badge + Controls
        # -------------------------------------------------------------
        toolbar_layout = QtWidgets.QHBoxLayout()
        toolbar_layout.setSpacing(8)

        # Channel Selector
        lbl_ch = QtWidgets.QLabel("Kanal:")
        lbl_ch.setStyleSheet("font-weight: bold; color: #CCCCCC; font-size: 11px;")
        toolbar_layout.addWidget(lbl_ch)

        self.combo_channel = QtWidgets.QComboBox()
        for k, info in self.channels.items():
            self.combo_channel.addItem(f"{info['name']} [{info['unit']}]", k)
        self.combo_channel.setCurrentIndex(0)  # Default EC
        self.combo_channel.setMinimumWidth(180)
        self.combo_channel.setStyleSheet("font-size: 11px; padding: 3px 6px; font-weight: bold;")
        toolbar_layout.addWidget(self.combo_channel)

        # Stability Indicator Badge
        self.lbl_stability_badge = QtWidgets.QLabel("● MENUNGGU DATA")
        self.lbl_stability_badge.setStyleSheet("""
            background-color: #242424;
            color: #9E9E9E;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        toolbar_layout.addWidget(self.lbl_stability_badge)

        toolbar_layout.addStretch()

        # Action Buttons: Pause/Live, Auto Scale, Zoom+, Zoom-, Reset
        self.btn_pause = QtWidgets.QPushButton("⏸ Pause")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setToolTip("Bekukan grafik untuk memeriksa titik dan melakukan zoom tanpa tergeser data baru")
        self.btn_pause.setStyleSheet("padding: 4px 10px; font-size: 11px;")

        self.btn_autoscale = QtWidgets.QPushButton("⟳ Auto Fit")
        self.btn_autoscale.setToolTip("Skala ulang otomatis sumbu X dan Y agar seluruh kurva terlihat optimal")
        self.btn_autoscale.setStyleSheet("background-color: #C62828; color: #FFFFFF; font-weight: bold; padding: 4px 10px; font-size: 11px;")

        self.btn_zoom_in = QtWidgets.QPushButton("🔍+")
        self.btn_zoom_in.setToolTip("Perbesar (Zoom In)")
        self.btn_zoom_in.setMaximumWidth(36)
        self.btn_zoom_in.setStyleSheet("padding: 4px 6px; font-size: 11px;")

        self.btn_zoom_out = QtWidgets.QPushButton("🔍-")
        self.btn_zoom_out.setToolTip("Perkecil (Zoom Out)")
        self.btn_zoom_out.setMaximumWidth(36)
        self.btn_zoom_out.setStyleSheet("padding: 4px 6px; font-size: 11px;")

        self.btn_clear = QtWidgets.QPushButton("🧹 Clear")
        self.btn_clear.setToolTip("Kosongkan data grafik")
        self.btn_clear.setStyleSheet("padding: 4px 10px; font-size: 11px;")

        toolbar_layout.addWidget(self.btn_pause)
        toolbar_layout.addWidget(self.btn_autoscale)
        toolbar_layout.addWidget(self.btn_zoom_in)
        toolbar_layout.addWidget(self.btn_zoom_out)
        toolbar_layout.addWidget(self.btn_clear)

        main_layout.addLayout(toolbar_layout)

        # -------------------------------------------------------------
        # 2. HUD INFO BAR: Hover Point Readout & Accurate Timestamps
        # -------------------------------------------------------------
        hud_frame = QtWidgets.QFrame()
        hud_frame.setStyleSheet("""
            QFrame {
                background-color: #151515;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                padding: 3px 8px;
            }
        """)
        hud_layout = QtWidgets.QHBoxLayout(hud_frame)
        hud_layout.setContentsMargins(6, 2, 6, 2)

        self.lbl_point_info = QtWidgets.QLabel("Arahkan kursor mouse ke grafik untuk melihat data titik dan timestamp akurat...")
        self.lbl_point_info.setStyleSheet("color: #64B5F6; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; font-weight: bold;")
        hud_layout.addWidget(self.lbl_point_info)

        hud_layout.addStretch()

        self.lbl_stats_summary = QtWidgets.QLabel("μ: -- | σ: -- | Min: -- | Max: --")
        self.lbl_stats_summary.setStyleSheet("color: #AAAAAA; font-family: 'Consolas', monospace; font-size: 11px;")
        hud_layout.addWidget(self.lbl_stats_summary)

        main_layout.addWidget(hud_frame)

        # -------------------------------------------------------------
        # 3. PYQTGRAPH PLOT WIDGET
        # -------------------------------------------------------------
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#121212")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)

        # Axis styling
        axis_pen = pg.mkPen(color="#757575", width=1)
        self.plot_widget.getAxis("bottom").setPen(axis_pen)
        self.plot_widget.getAxis("left").setPen(axis_pen)
        self.plot_widget.getAxis("bottom").setTextPen(pg.mkPen(color="#BDBDBD"))
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen(color="#BDBDBD"))

        self.plot_widget.setLabel("bottom", "Waktu Relatif (detik)")
        self.plot_widget.setLabel("left", "Konduktivitas (µS/cm)")

        # Main Curve
        cfg = self.channels[self.current_channel_key]
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color=cfg["color"], width=2.2),
            name=cfg["name"]
        )

        # Hover Point Scatter Highlight (Snapped Dot)
        self.hover_scatter = pg.ScatterPlotItem(
            size=10,
            pen=pg.mkPen(color="#FFFFFF", width=1.5),
            brush=pg.mkBrush(color="#FF1744")
        )
        self.plot_widget.addItem(self.hover_scatter)
        self.hover_scatter.setVisible(False)

        # Interactive Crosshair Lines (InfiniteLine)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FF5252', width=1, style=QtCore.Qt.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#FF5252', width=1, style=QtCore.Qt.DashLine))
        self.v_line.setVisible(False)
        self.h_line.setVisible(False)
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)

        # Connect mouse move event via SignalProxy
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved)

        main_layout.addWidget(self.plot_widget, stretch=1)

    def _connect_signals(self):
        self.combo_channel.currentIndexChanged.connect(self._on_channel_selected)
        self.btn_pause.toggled.connect(self._on_pause_toggled)
        self.btn_autoscale.clicked.connect(self.auto_fit_view)
        self.btn_zoom_in.clicked.connect(self._on_zoom_in_clicked)
        self.btn_zoom_out.clicked.connect(self._on_zoom_out_clicked)
        self.btn_clear.clicked.connect(self.clear_buffer)

    def _on_channel_selected(self, idx: int):
        new_key = self.combo_channel.itemData(idx)
        if not new_key or new_key == self.current_channel_key:
            return

        self.current_channel_key = new_key
        cfg = self.channels[self.current_channel_key]

        # Update curve color and axes labels
        self.curve.setPen(pg.mkPen(color=cfg["color"], width=2.2))
        self.plot_widget.setLabel("left", f"{cfg['name']} ({cfg['unit']})")

        # Update detector threshold
        self.detector.std_threshold = cfg["threshold"]
        self.detector.window_size = cfg["window"]
        self.clear_buffer()

    def _on_pause_toggled(self, paused: bool):
        self.is_paused = paused
        if paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet("background-color: #2E7D32; color: #FFFFFF; font-weight: bold; padding: 4px 10px; font-size: 11px;")
            self.lbl_point_info.setText("⏸ STREAM DI-PAUSE: Anda dapat bebas zoom & arahkan kursor ke titik kurva untuk inspeksi detail.")
        else:
            self.btn_pause.setText("⏸ Pause")
            self.btn_pause.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            self.auto_fit_view()

    def _on_zoom_in_clicked(self):
        view_box = self.plot_widget.getViewBox()
        view_box.scaleBy((0.7, 0.7))

    def _on_zoom_out_clicked(self):
        view_box = self.plot_widget.getViewBox()
        view_box.scaleBy((1.4, 1.4))

    def clear_buffer(self):
        self.buffer_timestamps.clear()
        self.buffer_time_floats.clear()
        self.buffer_values.clear()
        self.buffer_teensy_ms.clear()
        self.sample_counter = 0
        self.first_time_epoch = None
        self.detector.clear()
        self.curve.clear()
        self.hover_scatter.setVisible(False)
        self.v_line.setVisible(False)
        self.h_line.setVisible(False)
        self.lbl_stability_badge.setText("● MENUNGGU DATA")
        self.lbl_stability_badge.setStyleSheet("""
            background-color: #242424;
            color: #9E9E9E;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.lbl_stats_summary.setText("μ: -- | σ: -- | Min: -- | Max: --")
        self.lbl_point_info.setText("Data grafik telah dikosongkan. Menunggu sampel baru...")

    def add_telemetry(self, telemetry: dict):
        """
        Receives real-time telemetry dictionary from CommClient.
        Runs at telemetry stream frequency (e.g. 10 Hz).
        """
        cfg = self.channels[self.current_channel_key]
        raw_val = telemetry.get(cfg["key"], 0.0)

        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            return

        now = datetime.now()
        now_epoch = now.timestamp()
        if self.first_time_epoch is None:
            self.first_time_epoch = now_epoch

        elapsed_sec = now_epoch - self.first_time_epoch
        teensy_ms = telemetry.get("ts", 0)

        self.sample_counter += 1
        self.buffer_timestamps.append(now)
        self.buffer_time_floats.append(elapsed_sec)
        self.buffer_values.append(val)
        self.buffer_teensy_ms.append(teensy_ms)

        # Update stability detector
        self.detector.add_sample(val)

        # If not paused, update curve and live statistics
        if not self.is_paused:
            x_arr = np.array(self.buffer_time_floats, dtype=np.float64)
            y_arr = np.array(self.buffer_values, dtype=np.float64)
            self.curve.setData(x_arr, y_arr)

            # Auto-scroll view along X axis if buffer is large
            if len(x_arr) >= 2 and self.auto_scroll:
                x_max = x_arr[-1]
                x_min = max(0.0, x_max - 60.0)  # Show trailing 60 seconds by default
                self.plot_widget.setXRange(x_min, x_max + 1.0, padding=0.01)

                # Dynamic Y Range
                self._apply_smart_y_range(y_arr)

            self._update_stats_display(y_arr, cfg)

    def _apply_smart_y_range(self, y_arr: np.ndarray):
        """Calculates smart Y-axis limits with padding so small signals are prominent."""
        if len(y_arr) == 0:
            return

        # Use recent window (last 60 samples or full)
        recent_y = y_arr[-80:] if len(y_arr) >= 80 else y_arr
        y_min = float(np.nanmin(recent_y))
        y_max = float(np.nanmax(recent_y))
        span = y_max - y_min

        if span < 1e-4:
            # Flat line: expand around it nicely
            padding = 1.0 if abs(y_max) < 2.0 else abs(y_max) * 0.05
            self.plot_widget.setYRange(y_min - padding, y_max + padding, padding=0.02)
        else:
            padding = span * 0.12  # 12% margin
            self.plot_widget.setYRange(y_min - padding, y_max + padding, padding=0.01)

    def auto_fit_view(self):
        """Immediately scales the view to fit all currently buffered data points."""
        if len(self.buffer_values) == 0:
            return

        x_arr = np.array(self.buffer_time_floats, dtype=np.float64)
        y_arr = np.array(self.buffer_values, dtype=np.float64)

        x_min = float(np.min(x_arr))
        x_max = float(np.max(x_arr))
        y_min = float(np.min(y_arr))
        y_max = float(np.max(y_arr))

        x_span = x_max - x_min
        y_span = y_max - y_min

        x_pad = 0.5 if x_span < 1e-3 else x_span * 0.03
        y_pad = 0.5 if y_span < 1e-3 else y_span * 0.08

        self.plot_widget.setXRange(x_min - x_pad, x_max + x_pad, padding=0.0)
        self.plot_widget.setYRange(y_min - y_pad, y_max + y_pad, padding=0.0)

    def _update_stats_display(self, y_arr: np.ndarray, cfg: dict):
        stats = self.detector.get_stats()
        fmt = cfg["format"]
        unit = cfg["unit"]

        if len(y_arr) > 0:
            cur_mean = float(np.mean(y_arr))
            cur_std = float(np.std(y_arr))
            cur_min = float(np.min(y_arr))
            cur_max = float(np.max(y_arr))
            self.lbl_stats_summary.setText(
                f"μ: {cur_mean:.2f} | σ: {cur_std:.2f} | Min: {cur_min:.1f} | Max: {cur_max:.1f} {unit}"
            )

        # Update stability indicator badge
        if not stats["ready"]:
            self.lbl_stability_badge.setText(f"● MENGUMPULKAN DATA ({stats['count']}/{self.detector.window_size})")
            self.lbl_stability_badge.setStyleSheet("""
                background-color: #242424;
                color: #B0BEC5;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            """)
        elif stats["is_stable"]:
            std_str = fmt.format(stats['std'])
            p2p_str = fmt.format(stats['p2p'])
            self.lbl_stability_badge.setText(
                f"● STABIL / SIAP KALIBRASI (σ={std_str} | Δ={p2p_str} {unit})"
            )
            self.lbl_stability_badge.setStyleSheet("""
                background-color: #1B5E20;
                color: #FFFFFF;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            std_str = fmt.format(stats['std'])
            p2p_str = fmt.format(stats['p2p'])
            self.lbl_stability_badge.setText(
                f"● FLUKTUATIF / MENUNGGU (σ={std_str} | Δ={p2p_str} {unit})"
            )
            self.lbl_stability_badge.setStyleSheet("""
                background-color: #E65100;
                color: #FFFFFF;
                border: 1px solid #FF9800;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            """)

    def _on_mouse_moved(self, evt):
        """
        Handles mouse hover over plot to position crosshairs, snap to the nearest data point,
        and display high-precision timestamp with millisecond resolution.
        """
        pos = evt[0]
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self.v_line.setVisible(False)
            self.h_line.setVisible(False)
            self.hover_scatter.setVisible(False)
            return

        if len(self.buffer_time_floats) == 0:
            return

        mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
        mx = mouse_point.x()

        x_list = list(self.buffer_time_floats)
        y_list = list(self.buffer_values)
        ts_list = list(self.buffer_timestamps)
        tms_list = list(self.buffer_teensy_ms)

        # Find closest index
        diffs = np.abs(np.array(x_list) - mx)
        idx = int(np.argmin(diffs))

        nearest_x = x_list[idx]
        nearest_y = y_list[idx]
        nearest_dt = ts_list[idx]
        nearest_tms = tms_list[idx]

        # Update crosshairs
        self.v_line.setPos(nearest_x)
        self.h_line.setPos(nearest_y)
        self.v_line.setVisible(True)
        self.h_line.setVisible(True)

        # Update hover scatter marker
        self.hover_scatter.setData([nearest_x], [nearest_y])
        self.hover_scatter.setVisible(True)

        # Precise Millisecond Timestamp
        time_str = nearest_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cfg = self.channels[self.current_channel_key]
        val_str = cfg["format"].format(nearest_y)
        unit = cfg["unit"]

        # Calculate sample index (relative to total)
        total_samples = len(x_list)
        idx_display = idx + 1

        self.lbl_point_info.setText(
            f"📍 [Titik #{idx_display}/{total_samples}] "
            f"Waktu: <b>{time_str}</b> (+{nearest_x:.2f}s) | "
            f"<b>{cfg['name']}: {val_str} {unit}</b> | "
            f"Teensy: {nearest_tms} ms"
        )
