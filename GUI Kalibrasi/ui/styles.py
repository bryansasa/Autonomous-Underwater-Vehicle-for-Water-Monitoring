# -*- coding: utf-8 -*-
"""
Minimalist Industrial Matte Dark Theme (Red Accent) for GUI Kalibrasi
Matches Submersible Monitor industrial dark palette with dynamic zoom scaling.
"""


def get_wgg_stylesheet(zoom_factor: float = 1.0) -> str:
    base_size = int(12 * zoom_factor)
    small_size = int(11 * zoom_factor)
    large_size = int(16 * zoom_factor)

    return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: #181818;
            color: #E0E0E0;
            font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            font-size: {base_size}px;
        }}
        QGroupBox {{
            background-color: #222222;
            border: 1px solid #333333;
            border-radius: 4px;
            margin-top: 14px;
            padding-top: 14px;
            font-weight: bold;
            color: #E0E0E0;
            font-size: {base_size}px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 8px;
            color: #FFFFFF;
        }}
        QLabel {{
            color: #E0E0E0;
            font-size: {base_size}px;
        }}
        QLabel#lbl_rt_ph, QLabel#lbl_rt_ec, QLabel#lbl_rt_do, QLabel#lbl_rt_temp,
        QLabel#lbl_rt_roll, QLabel#lbl_rt_pitch, QLabel#lbl_rt_yaw, QLabel#lbl_rt_depth {{
            font-size: {large_size}px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
            color: #FFFFFF;
        }}
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
            background-color: #1A1A1A;
            border: 1px solid #383838;
            border-radius: 4px;
            padding: 4px 8px;
            color: #E0E0E0;
            font-size: {base_size}px;
        }}
        QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid #E53935;
            background-color: #202020;
        }}
        QComboBox::drop-down {{
            width: 20px;
            border-left: 1px solid #383838;
        }}
        QComboBox QAbstractItemView {{
            background-color: #222222;
            border: 1px solid #383838;
            selection-background-color: #D32F2F;
            selection-color: #FFFFFF;
            color: #E0E0E0;
        }}
        QPushButton {{
            background-color: #333333;
            color: #E0E0E0;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 6px 14px;
            font-size: {base_size}px;
            font-weight: bold;
            min-height: 22px;
        }}
        QPushButton:hover {{
            background-color: #444444;
            border: 1px solid #666666;
            color: #FFFFFF;
        }}
        QPushButton:pressed {{
            background-color: #1A1A1A;
        }}
        QPushButton:checked {{
            background-color: #D32F2F;
            color: #FFFFFF;
            border: 1px solid #E53935;
        }}
        QPushButton#btn_ph_mid, QPushButton#btn_ph_low, QPushButton#btn_ph_high {{
            background-color: #383838;
            border: 1px solid #484848;
        }}
        QPushButton#btn_ph_mid:hover, QPushButton#btn_ph_low:hover, QPushButton#btn_ph_high:hover {{
            background-color: #4A4A4A;
            border: 1px solid #E53935;
        }}
        QPushButton#btn_ph_clear, QPushButton#btn_ec_clear, QPushButton#btn_do_clear, QPushButton#btn_temp_clear {{
            background-color: #5C1D1D;
            border: 1px solid #8E2525;
            color: #FFFFFF;
        }}
        QPushButton#btn_ph_clear:hover, QPushButton#btn_ec_clear:hover, QPushButton#btn_do_clear:hover, QPushButton#btn_temp_clear:hover {{
            background-color: #7C2D2D;
        }}
        QPushButton#btn_temp_ice {{
            background-color: #0277BD;
            border: 1px solid #039BE5;
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton#btn_temp_ice:hover {{
            background-color: #0288D1;
            border: 1px solid #4FC3F7;
        }}
        QPushButton#btn_temp_custom {{
            background-color: #E65100;
            border: 1px solid #FF9800;
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton#btn_temp_custom:hover {{
            background-color: #F57C00;
            border: 1px solid #FFE0B2;
        }}
        QPushButton#btn_ec_dry {{
            background-color: #795548;
            border: 1px solid #A1887F;
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton#btn_ec_dry:hover {{
            background-color: #8D6E63;
            border: 1px solid #FFCC80;
        }}
        QPushButton#btn_ec_one {{
            background-color: #E65100;
            border: 1px solid #FF9800;
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton#btn_ec_one:hover {{
            background-color: #F57C00;
            border: 1px solid #FFE0B2;
        }}
        QPushButton#btn_ec_low, QPushButton#btn_ec_high {{
            background-color: #37474F;
            border: 1px solid #546E7A;
            color: #ECEFF1;
        }}
        QPushButton#btn_ec_low:hover, QPushButton#btn_ec_high:hover {{
            background-color: #455A64;
            border: 1px solid #90A4AE;
        }}
        QFrame#calPlotterFrame {{
            background-color: #1A1A1A;
            border: 1px solid #333333;
            border-radius: 6px;
        }}
        QSplitter::handle {{
            background-color: #2A2A2A;
            width: 4px;
            height: 4px;
        }}
        QSplitter::handle:hover {{
            background-color: #E53935;
        }}
        QPushButton#btn_gyro_cal, QPushButton#btn_mag_stream {{
            background-color: #383838;
            border: 1px solid #484848;
        }}
        QPushButton#btn_gyro_cal:hover, QPushButton#btn_mag_stream:hover {{
            background-color: #4A4A4A;
            border: 1px solid #E53935;
        }}
        QPushButton#btn_level_tare, QPushButton#btn_depth_tare {{
            background-color: #D32F2F;
            border: 1px solid #B71C1C;
            color: #FFFFFF;
        }}
        QPushButton#btn_level_tare:hover, QPushButton#btn_depth_tare:hover {{
            background-color: #E53935;
            border: 1px solid #D32F2F;
        }}
        QPushButton#btn_record {{
            background-color: #333333;
            border: 1px solid #444444;
        }}
        QPushButton#btn_record:checked {{
            background-color: #C62828;
            color: #FFFFFF;
            border: 1px solid #B71C1C;
        }}
        QTabWidget::pane {{
            border: 1px solid #333333;
            background-color: #222222;
            border-radius: 4px;
        }}
        QTabBar::tab {{
            background-color: #242424;
            color: #9E9E9E;
            padding: 7px 16px;
            margin-right: 2px;
            border: 1px solid #333333;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background-color: #181818;
            color: #FFFFFF;
            border-top: 2px solid #E53935;
            border-bottom: 2px solid #181818;
            font-weight: 700;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: #2C2C2C;
            color: #E0E0E0;
        }}
        QTextBrowser {{
            background-color: #141414;
            border: 1px solid #333333;
            border-radius: 4px;
            color: #C8C8C8;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: {small_size}px;
            padding: 4px;
        }}
        QScrollBar:vertical {{
            border: none;
            background-color: #181818;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: #383838;
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: #E53935;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background-color: #181818;
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: #383838;
            min-width: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: #E53935;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """
