# -*- coding: utf-8 -*-
"""
Submersible Calibration Suite — Tyrant-AQ
Application for calibrating Water Quality sensors (pH, EC, DO, Temp)
and Robot Orientation/Motion sensors (IMU Gyro, Leveling, Magnetometer, Depth).
"""

import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui

# Ensure workspace paths are accessible
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from ui.main_window import MainWindow


def main():
    # Enable High DPI scaling
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Submersible Calibration Suite")

    # Set default modern clean font
    app_font = QtGui.QFont("Segoe UI", 10)
    app.setFont(app_font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
