# -*- coding: utf-8 -*-
"""
Metric Card Widget
Minimalist Industrial Matte Dark card for real-time sensor readout.
"""

from PyQt5 import QtWidgets, QtCore, QtGui


class MetricCard(QtWidgets.QFrame):
    def __init__(self, title: str, unit: str = "", default_val: str = "--", accent_color: str = "#3b82f6", parent=None):
        super().__init__(parent)
        self.accent_color = accent_color
        self.unit = unit

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("""
            MetricCard {
                background-color: #141722;
                border: 1px solid #232a3c;
                border-radius: 6px;
            }
            MetricCard:hover {
                border-color: #38bdf8;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header: Title + Unit
        header_layout = QtWidgets.QHBoxLayout()
        self.lbl_title = QtWidgets.QLabel(title.upper())
        self.lbl_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;")
        
        self.lbl_unit = QtWidgets.QLabel(unit)
        self.lbl_unit.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_unit)
        layout.addLayout(header_layout)

        # Body: Value Display
        self.lbl_value = QtWidgets.QLabel(default_val)
        self.lbl_value.setStyleSheet("color: #f8fafc; font-size: 20px; font-weight: 700; font-family: 'Consolas', monospace;")
        self.lbl_value.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        layout.addWidget(self.lbl_value)

        # Footer: Subtitle / Stability indicator
        self.lbl_status = QtWidgets.QLabel("● Menunggu data...")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 9.5px; font-weight: 500;")
        layout.addWidget(self.lbl_status)

    def set_value(self, val_str: str, color_override: str = None):
        self.lbl_value.setText(val_str)
        c = color_override if color_override else "#f8fafc"
        self.lbl_value.setStyleSheet(f"color: {c}; font-size: 20px; font-weight: 700; font-family: 'Consolas', monospace;")

    def set_status(self, text: str, color_hex: str = "#94a3b8"):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {color_hex}; font-size: 9.5px; font-weight: 500;")
