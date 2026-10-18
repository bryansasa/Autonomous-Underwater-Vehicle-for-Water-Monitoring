# -*- coding: utf-8 -*-
"""
Water Quality & Power Management Tab for Submersible GCS
Consolidates:
  - Real-Time Water Quality Matrix (PP No. 22 / 2021 Baku Mutu Air Kelas 2)
  - Kalman 1D Filtered Power & Battery Management
  - EA-DSRA Dynamic Sampling Intervals (TBM)
"""
from typing import Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui

from ui.widgets.water_quality_card import WaterQualityCard
from ui.widgets.power_dsra_widget import PowerDSRAWidget


class WaterPowerTab(QtWidgets.QWidget):
    """
    Dedicated Tab for Saguling Water Quality Assessment & Power Management.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        root_layout = QtWidgets.QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(10)

        # Left Column: Water Quality Matrix (PP 22/2021)
        self.wq_card = WaterQualityCard()
        self.wq_card.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        root_layout.addWidget(self.wq_card, stretch=6)

        # Right Column: Power Management & EA-DSRA
        self.power_widget = PowerDSRAWidget()
        self.power_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        root_layout.addWidget(self.power_widget, stretch=5)

    def update_telemetry(self, data: Dict[str, Any]):
        """Forward telemetry data to both sub-widgets."""
        self.wq_card.update_telemetry(data)
        self.power_widget.update_telemetry(data)

    def apply_theme(self, theme_name: str):
        """Propagate theme changes to sub-widgets."""
        if hasattr(self.power_widget, "apply_theme"):
            self.power_widget.apply_theme(theme_name)
        if hasattr(self.wq_card, "apply_theme"):
            self.wq_card.apply_theme(theme_name)

