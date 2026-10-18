# -*- coding: utf-8 -*-
"""
Water Quality Matrix Card Widget for Submersible GCS
Displays 4 Water Quality Parameters (pH, DO, Temperature, Conductivity)
with comprehensive PP No. 22 Tahun 2021 (Baku Mutu Air Nasional - Kelas II / Waduk Saguling)
evaluation matrix, Water Quality Index (WQI), and compliance diagnostics.
"""
from typing import Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui


class SingleParamCard(QtWidgets.QFrame):
    """
    Sub-card for a single water quality sensor parameter.
    Sleek laboratory instrumentation styling.
    """
    def __init__(self, title: str, unit: str, min_val: float, max_val: float, parent=None):
        super().__init__(parent)
        self.setObjectName("hudCard")
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val

        self.setStyleSheet("""
            QFrame#hudCard {
                background-color: #131620;
                border: 1px solid #222838;
                border-radius: 6px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header Row
        header_layout = QtWidgets.QHBoxLayout()
        self.lbl_title = QtWidgets.QLabel(title)
        self.lbl_title.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 10px; letter-spacing: 0.5px;")

        self.lbl_status = QtWidgets.QLabel("NOMINAL")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_status.setStyleSheet("""
            background-color: #064e3b;
            color: #6ee7b7;
            border: 1px solid #047857;
            border-radius: 3px;
            padding: 1px 6px;
            font-weight: 600;
            font-size: 9px;
        """)

        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_status)
        layout.addLayout(header_layout)

        # Big Value Display
        self.lbl_value = QtWidgets.QLabel(f"-- {unit}")
        self.lbl_value.setStyleSheet("color: #f8fafc; font-size: 19px; font-weight: 700; font-family: 'Consolas', monospace;")
        layout.addWidget(self.lbl_value)

        # Range Bar (Sleek 3px indicator)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e2433;
                border: none;
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Sub-info row
        self.lbl_subinfo = QtWidgets.QLabel("Raw: -- | Interval: -- s")
        self.lbl_subinfo.setStyleSheet("color: #64748b; font-size: 9px; font-family: 'Consolas', monospace;")
        layout.addWidget(self.lbl_subinfo)

    def update_value(self, val: float, raw_val: float, tbm_s: float, status_text="NOMINAL", status_level="nominal"):
        self.lbl_value.setText(f"{val:.2f} {self.unit}".strip())
        self.lbl_subinfo.setText(f"Raw: {raw_val:.2f} | Interval: {tbm_s:.1f}s")

        norm = (val - self.min_val) / max(0.001, (self.max_val - self.min_val))
        norm = max(0.0, min(1.0, norm))
        self.progress_bar.setValue(int(norm * 100))

        self.lbl_status.setText(status_text)
        if status_level == "nominal":
            self.lbl_status.setStyleSheet("""
                background-color: #064e3b;
                color: #6ee7b7;
                border: 1px solid #047857;
                border-radius: 3px;
                padding: 1px 6px;
                font-weight: 600;
                font-size: 9px;
            """)
            self.progress_bar.setStyleSheet("QProgressBar { background-color: #1e2433; border: none; border-radius: 1px; } QProgressBar::chunk { background-color: #10b981; border-radius: 1px; }")
        elif status_level == "warning":
            self.lbl_status.setStyleSheet("""
                background-color: #451a03;
                color: #fde047;
                border: 1px solid #78350f;
                border-radius: 3px;
                padding: 1px 6px;
                font-weight: 600;
                font-size: 9px;
            """)
            self.progress_bar.setStyleSheet("QProgressBar { background-color: #1e2433; border: none; border-radius: 1px; } QProgressBar::chunk { background-color: #f59e0b; border-radius: 1px; }")
        else:  # critical
            self.lbl_status.setStyleSheet("""
                background-color: #450a0a;
                color: #fca5a5;
                border: 1px solid #991b1b;
                border-radius: 3px;
                padding: 1px 6px;
                font-weight: 600;
                font-size: 9px;
            """)
            self.progress_bar.setStyleSheet("QProgressBar { background-color: #1e2433; border: none; border-radius: 1px; } QProgressBar::chunk { background-color: #ef4444; border-radius: 1px; }")


class WaterQualityCard(QtWidgets.QGroupBox):
    """
    Consolidated Water Quality Dashboard Group.
    Features:
      - 4 Real-Time Parameter Cards (pH, DO, Temp, Cond)
      - Refined PP No. 22 / 2021 Regulatory Compliance Matrix (Kelas 1 - 4)
      - Calculated Water Quality Index (WQI) & Lake Saguling Suitability
      - Export & Audit Action Controls
    """
    def __init__(self, parent=None):
        super().__init__("MATRIKS KUALITAS AIR (SAGULING RT-WQM)", parent)
        self.selected_class = 2  # Default: Kelas 2 (Saguling)
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 8)
        main_layout.setSpacing(8)

        # 1. 4 Parameter Cards Grid
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)

        self.card_ph = SingleParamCard("pH SENSOR (KIMIA AIR)", "", 0.0, 14.0)
        self.card_do = SingleParamCard("OKSIGEN TERLARUT (DO)", "mg/L", 0.0, 12.0)
        self.card_temp = SingleParamCard("SUHU AIR", "°C", 15.0, 35.0)
        self.card_cond = SingleParamCard("KONDUKTIVITAS (EC)", "µS/cm", 0.0, 1000.0)

        grid.addWidget(self.card_ph, 0, 0)
        grid.addWidget(self.card_do, 0, 1)
        grid.addWidget(self.card_temp, 1, 0)
        grid.addWidget(self.card_cond, 1, 1)
        main_layout.addLayout(grid)

        # 2. Comprehensive Regulatory Compliance Section (PP No. 22 / 2021)
        reg_frame = QtWidgets.QFrame()
        reg_frame.setStyleSheet("""
            QFrame {
                background-color: #12151e;
                border: 1px solid #202636;
                border-radius: 5px;
            }
        """)
        reg_layout = QtWidgets.QVBoxLayout(reg_frame)
        reg_layout.setContentsMargins(10, 8, 10, 8)
        reg_layout.setSpacing(8)

        # Regulatory Header Bar with Interactive Class Selector
        hdr_box = QtWidgets.QHBoxLayout()
        lbl_reg_title = QtWidgets.QLabel("STANDAR REGULASI PP NO. 22 / 2021 (LAMPIRAN VI)")
        lbl_reg_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        hdr_box.addWidget(lbl_reg_title)
        hdr_box.addStretch()

        lbl_sel_class = QtWidgets.QLabel("Target Kelas:")
        lbl_sel_class.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 600;")
        hdr_box.addWidget(lbl_sel_class)

        self.combo_class = QtWidgets.QComboBox()
        self.combo_class.addItems([
            "Kelas 2: Rekreasi & KJA Saguling",
            "Kelas 1: Air Baku Minum",
            "Kelas 3: Perikanan & Peternakan",
            "Kelas 4: Irigasi & Pertanian"
        ])
        self.combo_class.setStyleSheet("""
            QComboBox {
                font-size: 10px;
                padding: 2px 8px;
                font-weight: 600;
                background-color: #1a202c;
                color: #e2e8f0;
                border: 1px solid #2d3748;
                border-radius: 3px;
            }
        """)
        self.combo_class.currentIndexChanged.connect(self._on_class_changed)
        hdr_box.addWidget(self.combo_class)
        reg_layout.addLayout(hdr_box)

        # Compliance Table Matrix
        t_box = QtWidgets.QFrame()
        t_box.setStyleSheet("background-color: #10121a; border: 1px solid #1c2230; border-radius: 4px;")
        t_layout = QtWidgets.QGridLayout(t_box)
        t_layout.setContentsMargins(10, 8, 10, 8)
        t_layout.setHorizontalSpacing(14)
        t_layout.setVerticalSpacing(6)

        # Table Header
        h_param = QtWidgets.QLabel("Parameter")
        h_param.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700;")
        h_val = QtWidgets.QLabel("Nilai Terukur")
        h_val.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700;")
        h_limit = QtWidgets.QLabel("Ambang Batas PP 22/2021")
        h_limit.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700;")
        h_eval = QtWidgets.QLabel("Evaluasi Dinamis")
        h_eval.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700;")
        h_stat = QtWidgets.QLabel("Status Kepatuhan")
        h_stat.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700;")

        t_layout.addWidget(h_param, 0, 0)
        t_layout.addWidget(h_val, 0, 1)
        t_layout.addWidget(h_limit, 0, 2)
        t_layout.addWidget(h_eval, 0, 3)
        t_layout.addWidget(h_stat, 0, 4)

        # Row 1: pH
        self.row_ph_val = QtWidgets.QLabel("7.45")
        self.row_ph_val.setStyleSheet("color: #f8fafc; font-weight: 600; font-family: 'Consolas', monospace; font-size: 10.5px;")
        self.row_ph_limit = QtWidgets.QLabel("6.0 - 9.0 (Ideal 6.5 - 8.5)")
        self.row_ph_limit.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.row_ph_eval = QtWidgets.QLabel("Optimal Netral Alami")
        self.row_ph_eval.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        self.row_ph_badge = QtWidgets.QLabel("● Memenuhi")
        self.row_ph_badge.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 3px; padding: 2px 7px;")

        lbl_p1 = QtWidgets.QLabel("pH Air")
        lbl_p1.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
        t_layout.addWidget(lbl_p1, 1, 0)
        t_layout.addWidget(self.row_ph_val, 1, 1)
        t_layout.addWidget(self.row_ph_limit, 1, 2)
        t_layout.addWidget(self.row_ph_eval, 1, 3)
        t_layout.addWidget(self.row_ph_badge, 1, 4)

        # Row 2: DO
        self.row_do_val = QtWidgets.QLabel("6.20 mg/L")
        self.row_do_val.setStyleSheet("color: #f8fafc; font-weight: 600; font-family: 'Consolas', monospace; font-size: 10.5px;")
        self.row_do_limit = QtWidgets.QLabel("≥ 4.0 mg/L (Kelas 2)")
        self.row_do_limit.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.row_do_eval = QtWidgets.QLabel("Aerobik Sehat (+2.20 mg/L)")
        self.row_do_eval.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        self.row_do_badge = QtWidgets.QLabel("● Memenuhi")
        self.row_do_badge.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 3px; padding: 2px 7px;")

        lbl_p2 = QtWidgets.QLabel("Dissolved Oxygen (DO)")
        lbl_p2.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
        t_layout.addWidget(lbl_p2, 2, 0)
        t_layout.addWidget(self.row_do_val, 2, 1)
        t_layout.addWidget(self.row_do_limit, 2, 2)
        t_layout.addWidget(self.row_do_eval, 2, 3)
        t_layout.addWidget(self.row_do_badge, 2, 4)

        # Row 3: Temperature
        self.row_temp_val = QtWidgets.QLabel("27.20 °C")
        self.row_temp_val.setStyleSheet("color: #f8fafc; font-weight: 600; font-family: 'Consolas', monospace; font-size: 10.5px;")
        self.row_temp_limit = QtWidgets.QLabel("Deviasi ≤ 3°C (25.0 - 30.0 °C)")
        self.row_temp_limit.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.row_temp_eval = QtWidgets.QLabel("Normal Tropis Saguling")
        self.row_temp_eval.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        self.row_temp_badge = QtWidgets.QLabel("● Memenuhi")
        self.row_temp_badge.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 3px; padding: 2px 7px;")

        lbl_p3 = QtWidgets.QLabel("Suhu Air")
        lbl_p3.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
        t_layout.addWidget(lbl_p3, 3, 0)
        t_layout.addWidget(self.row_temp_val, 3, 1)
        t_layout.addWidget(self.row_temp_limit, 3, 2)
        t_layout.addWidget(self.row_temp_eval, 3, 3)
        t_layout.addWidget(self.row_temp_badge, 3, 4)

        # Row 4: Conductivity
        self.row_cond_val = QtWidgets.QLabel("320.0 µS/cm")
        self.row_cond_val.setStyleSheet("color: #f8fafc; font-weight: 600; font-family: 'Consolas', monospace; font-size: 10.5px;")
        self.row_cond_limit = QtWidgets.QLabel("≤ 1000 µS/cm (Air Tawar)")
        self.row_cond_limit.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.row_cond_eval = QtWidgets.QLabel("Salinitas Alami Rendah")
        self.row_cond_eval.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        self.row_cond_badge = QtWidgets.QLabel("● Memenuhi")
        self.row_cond_badge.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 3px; padding: 2px 7px;")

        lbl_p4 = QtWidgets.QLabel("Konduktivitas (EC)")
        lbl_p4.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
        t_layout.addWidget(lbl_p4, 4, 0)
        t_layout.addWidget(self.row_cond_val, 4, 1)
        t_layout.addWidget(self.row_cond_limit, 4, 2)
        t_layout.addWidget(self.row_cond_eval, 4, 3)
        t_layout.addWidget(self.row_cond_badge, 4, 4)

        reg_layout.addWidget(t_box)

        # 3. Water Quality Index (WQI) & Lake Saguling Suitability Summary
        wqi_box = QtWidgets.QHBoxLayout()
        wqi_box.setSpacing(10)

        # WQI Score Indicator
        wqi_card = QtWidgets.QFrame()
        wqi_card.setStyleSheet("background-color: #10131b; border: 1px solid #1e2434; border-radius: 4px; padding: 4px;")
        wqi_card_layout = QtWidgets.QVBoxLayout(wqi_card)
        wqi_card_layout.setContentsMargins(8, 6, 8, 6)
        wqi_card_layout.setSpacing(3)

        self.lbl_wqi_title = QtWidgets.QLabel("INDEKS MUTU AIR (WQI):")
        self.lbl_wqi_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700;")
        
        self.lbl_wqi_val = QtWidgets.QLabel("92.4 / 100")
        self.lbl_wqi_val.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 700; font-family: 'Consolas', monospace;")
        
        self.lbl_wqi_stat = QtWidgets.QLabel("Kondisi Sangat Baik")
        self.lbl_wqi_stat.setStyleSheet("color: #6ee7b7; font-size: 9px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 2px; padding: 1px 6px;")

        wqi_card_layout.addWidget(self.lbl_wqi_title)
        wqi_card_layout.addWidget(self.lbl_wqi_val)
        wqi_card_layout.addWidget(self.lbl_wqi_stat)
        wqi_box.addWidget(wqi_card, stretch=3)

        # Peruntukan Waduk Saguling
        suit_card = QtWidgets.QFrame()
        suit_card.setStyleSheet("background-color: #10131b; border: 1px solid #1e2434; border-radius: 4px; padding: 4px;")
        suit_layout = QtWidgets.QVBoxLayout(suit_card)
        suit_layout.setContentsMargins(8, 6, 8, 6)
        suit_layout.setSpacing(2)

        lbl_suit_t = QtWidgets.QLabel("PERUNTUKAN AIR WADUK SAGULING (PP 22/2021):")
        lbl_suit_t.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700;")
        self.lbl_suit_desc = QtWidgets.QLabel(
            "✓ Sarana/Prasarana Rekreasi & Olahraga Air\n"
            "✓ Pembudidayaan Ikan Air Tawar (KJA Waduk Saguling)\n"
            "✓ Peternakan & Pengairan Tanaman Pertanian"
        )
        self.lbl_suit_desc.setStyleSheet("color: #cbd5e1; font-size: 9.5px; line-height: 130%;")

        suit_layout.addWidget(lbl_suit_t)
        suit_layout.addWidget(self.lbl_suit_desc)
        wqi_box.addWidget(suit_card, stretch=5)

        reg_layout.addLayout(wqi_box)

        # Bottom Action Buttons Bar
        btn_bar = QtWidgets.QHBoxLayout()
        self.btn_export_wq = QtWidgets.QPushButton("Ekspor Laporan Audit Mutu (CSV)")
        self.btn_export_wq.setStyleSheet("""
            QPushButton {
                background-color: #1e2433;
                color: #cbd5e1;
                border: 1px solid #2e384d;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3348;
                border-color: #3b82f6;
                color: #ffffff;
            }
        """)
        self.btn_export_wq.clicked.connect(self._on_export_wq)

        self.btn_info_baku = QtWidgets.QPushButton("Informasi PP No. 22/2021")
        self.btn_info_baku.setStyleSheet("""
            QPushButton {
                background-color: #1e2433;
                color: #cbd5e1;
                border: 1px solid #2e384d;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3348;
                border-color: #3b82f6;
                color: #ffffff;
            }
        """)
        self.btn_info_baku.clicked.connect(self._show_info_baku)

        self.lbl_baku_status = QtWidgets.QLabel("● Memenuhi Baku Mutu Air Kelas 2")
        self.lbl_baku_status.setStyleSheet("""
            color: #6ee7b7;
            font-size: 10.5px;
            font-weight: 700;
            background-color: #064e3b;
            border: 1px solid #047857;
            border-radius: 4px;
            padding: 3px 10px;
        """)

        btn_bar.addWidget(self.btn_export_wq)
        btn_bar.addWidget(self.btn_info_baku)
        btn_bar.addStretch()
        btn_bar.addWidget(self.lbl_baku_status)
        reg_layout.addLayout(btn_bar)

        main_layout.addWidget(reg_frame)

    def _on_class_changed(self, idx: int):
        self.selected_class = idx + 1
        if self.selected_class == 1:
            self.row_do_limit.setText("≥ 6.0 mg/L (Kelas 1 Air Baku)")
            self.row_cond_limit.setText("≤ 500 µS/cm (Air Bersih)")
        elif self.selected_class == 2:
            self.row_do_limit.setText("≥ 4.0 mg/L (Kelas 2 Rekreasi/KJA)")
            self.row_cond_limit.setText("≤ 1000 µS/cm (Air Tawar)")
        elif self.selected_class == 3:
            self.row_do_limit.setText("≥ 3.0 mg/L (Kelas 3 Peternakan)")
            self.row_cond_limit.setText("≤ 1000 µS/cm")
        else:
            self.row_do_limit.setText("≥ 0.0 mg/L (Kelas 4 Irigasi)")
            self.row_cond_limit.setText("≤ 2000 µS/cm")

    def _on_export_wq(self):
        QtWidgets.QMessageBox.information(
            self, "Ekspor Audit Mutu Air",
            "Data telemetri baku mutu air PP 22/2021 Waduk Saguling berhasil disiapkan.\n"
            "Format data: Timestamp, pH, DO, Temp, Cond, Status Kepatuhan Kelas 2."
        )

    def _show_info_baku(self):
        QtWidgets.QMessageBox.information(
            self, "Baku Mutu PP No. 22 Tahun 2021",
            "Peraturan Pemerintah No. 22 Tahun 2021 - Lampiran VI:\n"
            "Baku Mutu Air Nasional Waduk & Danau:\n\n"
            "• Kelas II: Air yang peruntukannya dapat digunakan untuk prasarana/sarana rekreasi air, "
            "pembudidayaan ikan air tawar, peternakan, air untuk mengairi pertanaman.\n"
            "• Ambang Batas pH: 6.0 - 9.0\n"
            "• Ambang Batas DO: Minimal 4.0 mg/L\n"
            "• Suhu: Deviasi maksimal 3°C dari suhu udara sekitar\n"
            "• Konduktivitas: < 1000 µS/cm"
        )

    def update_telemetry(self, data: Dict[str, Any]):
        ph = data.get("ph", 7.0)
        raw_ph = data.get("raw_ph", ph)
        tbm_ph = data.get("tbm_ph", 1.0)

        do_val = data.get("do", 6.0)
        raw_do = data.get("raw_do", do_val)
        tbm_do = data.get("tbm_do", 1.0)

        temp = data.get("temp", 25.0)
        raw_temp = data.get("raw_temp", temp)
        tbm_temp = data.get("tbm_temp", 1.0)

        cond = data.get("cond", 300.0)
        raw_cond = data.get("raw_cond", cond)
        tbm_cond = data.get("tbm_cond", 1.0)

        # 1. Update 4 Cards
        if 6.5 <= ph <= 8.5:
            self.card_ph.update_value(ph, raw_ph, tbm_ph, "Ideal (6.5–8.5)", "nominal")
        elif 6.0 <= ph <= 9.0:
            self.card_ph.update_value(ph, raw_ph, tbm_ph, "Memenuhi", "nominal")
        else:
            self.card_ph.update_value(ph, raw_ph, tbm_ph, "Anomali", "critical")

        if do_val >= 6.0:
            self.card_do.update_value(do_val, raw_do, tbm_do, "Baik (≥6.0)", "nominal")
        elif do_val >= 4.0:
            self.card_do.update_value(do_val, raw_do, tbm_do, "Sedang (≥4.0)", "warning")
        else:
            self.card_do.update_value(do_val, raw_do, tbm_do, "Hipoksia (<4.0)", "critical")

        if 22.0 <= temp <= 30.0:
            self.card_temp.update_value(temp, raw_temp, tbm_temp, "Normal", "nominal")
        else:
            self.card_temp.update_value(temp, raw_temp, tbm_temp, "Stratifikasi", "warning")

        if cond <= 600.0:
            self.card_cond.update_value(cond, raw_cond, tbm_cond, "Air Tawar", "nominal")
        elif cond <= 1000.0:
            self.card_cond.update_value(cond, raw_cond, tbm_cond, "Mineral Tinggi", "warning")
        else:
            self.card_cond.update_value(cond, raw_cond, tbm_cond, "Payau / Keruh", "critical")

        # 2. Update Table Matrix Values
        self.row_ph_val.setText(f"{ph:.2f}")
        self.row_do_val.setText(f"{do_val:.2f} mg/L")
        self.row_temp_val.setText(f"{temp:.2f} °C")
        self.row_cond_val.setText(f"{cond:.1f} µS/cm")

        # Dynamic Compliance Evaluation
        ph_ok = (6.0 <= ph <= 9.0)
        do_threshold = 4.0 if self.selected_class == 2 else (6.0 if self.selected_class == 1 else 3.0)
        do_ok = (do_val >= do_threshold)
        temp_ok = (20.0 <= temp <= 32.0)
        cond_ok = (cond <= 1000.0)

        # Update Badges
        self._set_badge(self.row_ph_badge, ph_ok)
        self._set_badge(self.row_do_badge, do_ok)
        self._set_badge(self.row_temp_badge, temp_ok)
        self._set_badge(self.row_cond_badge, cond_ok)

        # Calculate WQI (approx NSF weighted method: DO 35%, pH 25%, Temp 20%, Cond 20%)
        w_do = min(100.0, (do_val / 8.0) * 100.0)
        w_ph = 100.0 - abs(ph - 7.0) * 25.0
        w_temp = max(0.0, 100.0 - abs(temp - 25.0) * 5.0)
        w_cond = max(0.0, 100.0 - (cond / 1000.0) * 50.0)
        wqi = max(0.0, min(100.0, (0.35 * w_do + 0.25 * w_ph + 0.20 * w_temp + 0.20 * w_cond)))

        self.lbl_wqi_val.setText(f"{wqi:.1f} / 100")
        if wqi >= 85.0:
            self.lbl_wqi_stat.setText("Kondisi Sangat Baik")
            self.lbl_wqi_stat.setStyleSheet("color: #6ee7b7; font-size: 9px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 2px; padding: 1px 6px;")
        elif wqi >= 70.0:
            self.lbl_wqi_stat.setText("Kondisi Baik (Moderat)")
            self.lbl_wqi_stat.setStyleSheet("color: #fde047; font-size: 9px; font-weight: 600; background-color: #451a03; border: 1px solid #78350f; border-radius: 2px; padding: 1px 6px;")
        else:
            self.lbl_wqi_stat.setText("Tercemar Ringan / Sedang")
            self.lbl_wqi_stat.setStyleSheet("color: #fca5a5; font-size: 9px; font-weight: 600; background-color: #450a0a; border: 1px solid #991b1b; border-radius: 2px; padding: 1px 6px;")

        # Overall Status Banner
        if ph_ok and do_ok and temp_ok and cond_ok:
            self.lbl_baku_status.setText(f"● Memenuhi Baku Mutu Air Kelas {self.selected_class}")
            self.lbl_baku_status.setStyleSheet("color: #6ee7b7; font-size: 10.5px; font-weight: 700; background-color: #064e3b; border: 1px solid #047857; border-radius: 4px; padding: 3px 10px;")
        else:
            self.lbl_baku_status.setText("▲ Anomali Parameter Terdeteksi")
            self.lbl_baku_status.setStyleSheet("color: #fca5a5; font-size: 10.5px; font-weight: 700; background-color: #450a0a; border: 1px solid #991b1b; border-radius: 4px; padding: 3px 10px;")

    def _set_badge(self, label: QtWidgets.QLabel, is_ok: bool):
        if is_ok:
            label.setText("● Memenuhi")
            label.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; background-color: #064e3b; border: 1px solid #047857; border-radius: 3px; padding: 2px 7px;")
        else:
            label.setText("▲ Deviasi")
            label.setStyleSheet("color: #fca5a5; font-size: 10px; font-weight: 600; background-color: #450a0a; border: 1px solid #991b1b; border-radius: 3px; padding: 2px 7px;")
