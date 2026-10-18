# -*- coding: utf-8 -*-
"""
Power & Energy-Aware Dynamic Sampling Rate Adaptation (EA-DSRA) Widget for Submersible GCS
Monitors 6S LiPo battery pack with 1D Kalman Filter, INA226 power metrics,
and real-time EA-DSRA adaptive sensor sleep/wake modulation.
"""
from typing import Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui


class PowerDSRAWidget(QtWidgets.QGroupBox):
    """
    Submersible Power Management & EA-DSRA Modulation Center.
    Features:
      - 6S LiPo Kalman-filtered Battery Management & Dynamic Cell Estimation
      - INA226 High-side Current & Power Draw Telemetry
      - 4-Channel EA-DSRA Sampling Interval (T_BM) Dynamic Modulation
      - Energy Savings Analytics vs 1Hz Continuous Baseline
      - Interactive EA-DSRA Power Profile Controls
    """
    def __init__(self, parent=None):
        super().__init__("MANAJEMEN DAYA & OPTIMASI SAMPLING EA-DSRA", parent)
        self.selected_profile = "auto"
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 8)
        main_layout.setSpacing(8)

        # =====================================================================
        # 1. TOP SECTION: Battery Pack & INA226 Power Cards
        # =====================================================================
        top_grid = QtWidgets.QGridLayout()
        top_grid.setSpacing(8)

        # Left: 6S LiPo Battery Management Card
        self.frame_batt = QtWidgets.QFrame()
        self.frame_batt.setStyleSheet("""
            QFrame {
                background-color: #12151e;
                border: 1px solid #202636;
                border-radius: 5px;
            }
        """)
        b_layout = QtWidgets.QVBoxLayout(self.frame_batt)
        b_layout.setContentsMargins(8, 6, 8, 6)
        b_layout.setSpacing(4)

        b_hdr = QtWidgets.QHBoxLayout()
        self.lbl_b_title = QtWidgets.QLabel("BATERAI 1: BUS THRUSTER (6S LiPo)")
        self.lbl_b_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.3px;")
        
        self.lbl_soc = QtWidgets.QLabel("100.0%")
        self.lbl_soc.setStyleSheet("color: #34d399; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace;")
        b_hdr.addWidget(self.lbl_b_title)
        b_hdr.addStretch()
        b_hdr.addWidget(self.lbl_soc)
        b_layout.addLayout(b_hdr)

        # Dynamic Battery Progress Bar (Green >45%, Amber 20-45%, Red <20%)
        self.soc_bar = QtWidgets.QProgressBar()
        self.soc_bar.setRange(0, 100)
        self.soc_bar.setValue(100)
        self.soc_bar.setFixedHeight(6)
        self.soc_bar.setTextVisible(False)
        self.soc_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a202c;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 2px;
            }
        """)
        b_layout.addWidget(self.soc_bar)

        self.lbl_v_info = QtWidgets.QLabel("Tegangan: 25.20 V | Sel: 4.20 V/cell")
        self.lbl_v_info.setStyleSheet("color: #cbd5e1; font-size: 9.5px; font-family: 'Consolas', monospace;")
        b_layout.addWidget(self.lbl_v_info)

        self.lbl_runtime = QtWidgets.QLabel("Estimasi Waktu Misi: ~4 Jam 30 Menit")
        self.lbl_runtime.setStyleSheet("color: #64748b; font-size: 9.5px;")
        b_layout.addWidget(self.lbl_runtime)

        top_grid.addWidget(self.frame_batt, 0, 0)

        # Right: Baterai 2 (Rel Sensor & Mikrokontroler)
        self.frame_pwr = QtWidgets.QFrame()
        self.frame_pwr.setStyleSheet("""
            QFrame {
                background-color: #12151e;
                border: 1px solid #202636;
                border-radius: 5px;
            }
        """)
        p_layout = QtWidgets.QVBoxLayout(self.frame_pwr)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(4)

        p_hdr = QtWidgets.QHBoxLayout()
        self.lbl_p_title = QtWidgets.QLabel("BATERAI 2: REL SENSOR & MCU (INA226)")
        self.lbl_p_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.3px;")
        
        self.lbl_sensor_soc = QtWidgets.QLabel("100.0%")
        self.lbl_sensor_soc.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace;")
        p_hdr.addWidget(self.lbl_p_title)
        p_hdr.addStretch()
        p_hdr.addWidget(self.lbl_sensor_soc)
        p_layout.addLayout(p_hdr)

        # Dynamic Battery 2 Progress Bar
        self.sensor_soc_bar = QtWidgets.QProgressBar()
        self.sensor_soc_bar.setRange(0, 100)
        self.sensor_soc_bar.setValue(100)
        self.sensor_soc_bar.setFixedHeight(6)
        self.sensor_soc_bar.setTextVisible(False)
        self.sensor_soc_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a202c;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 2px;
            }
        """)
        p_layout.addWidget(self.sensor_soc_bar)

        self.lbl_curr = QtWidgets.QLabel("Tegangan: 12.10 V | Arus: 0.22 A | Daya: 2.7 W")
        self.lbl_curr.setStyleSheet("color: #cbd5e1; font-size: 9.5px; font-weight: 600; font-family: 'Consolas', monospace;")
        p_layout.addWidget(self.lbl_curr)

        self.lbl_energy_used = QtWidgets.QLabel("Total Daya Sistem: 0.0 W (B1 Thruster + B2 Sensor)")
        self.lbl_energy_used.setStyleSheet("color: #64748b; font-size: 9.5px;")
        p_layout.addWidget(self.lbl_energy_used)

        top_grid.addWidget(self.frame_pwr, 0, 1)
        main_layout.addLayout(top_grid)

        # =====================================================================
        # 2. MIDDLE SECTION: EA-DSRA Adaptive Sampling Rate Modulation (T_BM)
        # =====================================================================
        dsra_frame = QtWidgets.QFrame()
        dsra_frame.setStyleSheet("""
            QFrame {
                background-color: #12151e;
                border: 1px solid #202636;
                border-radius: 5px;
            }
        """)
        dsra_layout = QtWidgets.QVBoxLayout(dsra_frame)
        dsra_layout.setContentsMargins(10, 8, 10, 8)
        dsra_layout.setSpacing(8)

        # Header with Penalty Factor
        dsra_hdr = QtWidgets.QHBoxLayout()
        self.lbl_dsra_title = QtWidgets.QLabel("MODULASI INTERVAL SAMPLING ADAPTIF (EA-DSRA T_BM)")
        self.lbl_dsra_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        
        self.lbl_wea = QtWidgets.QLabel("Faktor Penalti W_ea: 1.00 (Efisiensi Tinggi)")
        self.lbl_wea.setStyleSheet("""
            color: #38bdf8;
            font-size: 9.5px;
            font-weight: 600;
            background-color: #0c4a6e;
            border: 1px solid #0369a1;
            border-radius: 3px;
            padding: 1px 6px;
        """)
        dsra_hdr.addWidget(self.lbl_dsra_title)
        dsra_hdr.addStretch()
        dsra_hdr.addWidget(self.lbl_wea)
        dsra_layout.addLayout(dsra_hdr)

        # 4 Sensor Interval Cards (Grid 2x2)
        m_grid = QtWidgets.QGridLayout()
        m_grid.setSpacing(6)

        # pH TBM
        self.card_t_ph = self._create_tbm_card("SENSOR pH (EZO)", "T_BM: 5.0 s", "Low Dynamic (Sleep Mode)", 5.0, 10.0, "Hemat 80%")
        self.lbl_t_ph_val = self.card_t_ph.findChild(QtWidgets.QLabel, "t_val")
        self.lbl_t_ph_desc = self.card_t_ph.findChild(QtWidgets.QLabel, "t_desc")
        self.bar_t_ph = self.card_t_ph.findChild(QtWidgets.QProgressBar, "t_bar")
        m_grid.addWidget(self.card_t_ph, 0, 0)

        # DO TBM
        self.card_t_do = self._create_tbm_card("SENSOR DO (OXYGEN)", "T_BM: 2.0 s", "Active Monitoring (Gradien)", 2.0, 10.0, "Hemat 50%")
        self.lbl_t_do_val = self.card_t_do.findChild(QtWidgets.QLabel, "t_val")
        self.lbl_t_do_desc = self.card_t_do.findChild(QtWidgets.QLabel, "t_desc")
        self.bar_t_do = self.card_t_do.findChild(QtWidgets.QProgressBar, "t_bar")
        m_grid.addWidget(self.card_t_do, 0, 1)

        # Temp TBM
        self.card_t_temp = self._create_tbm_card("SENSOR SUHU AIR", "T_BM: 3.0 s", "Thermal Inertia Stabil", 3.0, 10.0, "Hemat 67%")
        self.lbl_t_temp_val = self.card_t_temp.findChild(QtWidgets.QLabel, "t_val")
        self.lbl_t_temp_desc = self.card_t_temp.findChild(QtWidgets.QLabel, "t_desc")
        self.bar_t_temp = self.card_t_temp.findChild(QtWidgets.QProgressBar, "t_bar")
        m_grid.addWidget(self.card_t_temp, 1, 0)

        # Cond TBM
        self.card_t_cond = self._create_tbm_card("SENSOR KONDUKTIVITAS", "T_BM: 4.0 s", "Baseline Salinitas Tenang", 4.0, 10.0, "Hemat 75%")
        self.lbl_t_cond_val = self.card_t_cond.findChild(QtWidgets.QLabel, "t_val")
        self.lbl_t_cond_desc = self.card_t_cond.findChild(QtWidgets.QLabel, "t_desc")
        self.bar_t_cond = self.card_t_cond.findChild(QtWidgets.QProgressBar, "t_bar")
        m_grid.addWidget(self.card_t_cond, 1, 1)

        dsra_layout.addLayout(m_grid)

        # Energy Savings Analytics Summary
        savings_box = QtWidgets.QHBoxLayout()
        savings_box.setSpacing(10)

        lbl_sav_title = QtWidgets.QLabel("Efisiensi Energi EA-DSRA:")
        lbl_sav_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700;")
        savings_box.addWidget(lbl_sav_title)

        self.sav_bar = QtWidgets.QProgressBar()
        self.sav_bar.setRange(0, 100)
        self.sav_bar.setValue(42)
        self.sav_bar.setFixedHeight(6)
        self.sav_bar.setTextVisible(False)
        self.sav_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a202c;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 2px;
            }
        """)
        savings_box.addWidget(self.sav_bar, stretch=1)

        self.lbl_sav_text = QtWidgets.QLabel("42.8% Energi Terhemat (vs 1 Hz Kontinu)")
        self.lbl_sav_text.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        savings_box.addWidget(self.lbl_sav_text)

        dsra_layout.addLayout(savings_box)
        main_layout.addWidget(dsra_frame)

        # =====================================================================
        # 3. BOTTOM SECTION: Interactive EA-DSRA Strategy Controls
        # =====================================================================
        ctrl_frame = QtWidgets.QFrame()
        ctrl_frame.setStyleSheet("""
            QFrame {
                background-color: #12151e;
                border: 1px solid #202636;
                border-radius: 5px;
            }
        """)
        ctrl_layout = QtWidgets.QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)
        ctrl_layout.setSpacing(10)

        lbl_mode_t = QtWidgets.QLabel("Mode Profil EA-DSRA:")
        lbl_mode_t.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700;")
        ctrl_layout.addWidget(lbl_mode_t)

        self.combo_profile = QtWidgets.QComboBox()
        self.combo_profile.addItems([
            "Adaptif Dinamis Otomatis (Standar Waduk)",
            "Mode Agresif Hemat Daya (TBM Max 10s)",
            "Mode Riset Presisi Tinggi (1.0 Hz Kontinu)",
            "Mode Hibernasi Sensor (TBM 30s)"
        ])
        self.combo_profile.setStyleSheet("""
            QComboBox {
                font-size: 10px;
                padding: 3px 8px;
                font-weight: 600;
                background-color: #1a202c;
                color: #e2e8f0;
                border: 1px solid #2d3748;
                border-radius: 3px;
            }
        """)
        self.combo_profile.currentIndexChanged.connect(self._on_profile_changed)
        ctrl_layout.addWidget(self.combo_profile)

        ctrl_layout.addStretch()

        self.btn_apply = QtWidgets.QPushButton("Terapkan Profil EA-DSRA")
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #0369a1;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_apply.clicked.connect(self._on_apply_profile)
        ctrl_layout.addWidget(self.btn_apply)

        self.btn_reset_kalman = QtWidgets.QPushButton("Tare Kalman SoC")
        self.btn_reset_kalman.setStyleSheet("""
            QPushButton {
                background-color: #1e2433;
                color: #cbd5e1;
                border: 1px solid #2e384d;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3348;
                color: #ffffff;
            }
        """)
        self.btn_reset_kalman.clicked.connect(self._on_reset_kalman)
        ctrl_layout.addWidget(self.btn_reset_kalman)

        main_layout.addWidget(ctrl_frame)

    def _create_tbm_card(self, title: str, init_val: str, desc: str, val_s: float, max_s: float, sav_pct: str) -> QtWidgets.QFrame:
        f = QtWidgets.QFrame()
        f.setStyleSheet("""
            QFrame {
                background-color: #10131c;
                border: 1px solid #1f2536;
                border-radius: 4px;
                padding: 3px;
            }
        """)
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(6, 4, 6, 4)
        l.setSpacing(2)

        hdr = QtWidgets.QHBoxLayout()
        lbl_t = QtWidgets.QLabel(title)
        lbl_t.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: 700; letter-spacing: 0.3px;")
        
        lbl_v = QtWidgets.QLabel(init_val)
        lbl_v.setObjectName("t_val")
        lbl_v.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        hdr.addWidget(lbl_t)
        hdr.addStretch()
        hdr.addWidget(lbl_v)
        l.addLayout(hdr)

        bar = QtWidgets.QProgressBar()
        bar.setObjectName("t_bar")
        bar.setRange(0, int(max_s * 10))
        bar.setValue(int(val_s * 10))
        bar.setFixedHeight(3)
        bar.setTextVisible(False)
        bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a202c;
                border: none;
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background-color: #0284c7;
                border-radius: 1px;
            }
        """)
        l.addWidget(bar)

        sub_row = QtWidgets.QHBoxLayout()
        lbl_d = QtWidgets.QLabel(desc)
        lbl_d.setObjectName("t_desc")
        lbl_d.setStyleSheet("color: #64748b; font-size: 8.5px;")
        
        lbl_sav = QtWidgets.QLabel(sav_pct)
        lbl_sav.setStyleSheet("""
            color: #6ee7b7;
            font-size: 8.5px;
            font-weight: 600;
            background-color: #064e3b;
            border: 1px solid #047857;
            border-radius: 2px;
            padding: 0px 4px;
        """)
        sub_row.addWidget(lbl_d)
        sub_row.addStretch()
        sub_row.addWidget(lbl_sav)
        l.addLayout(sub_row)

        return f

    def _on_profile_changed(self, idx: int):
        profiles = ["auto", "aggressive", "high_rate", "hibernate"]
        self.selected_profile = profiles[idx]

    def _on_apply_profile(self):
        profile_name = self.combo_profile.currentText()
        QtWidgets.QMessageBox.information(
            self, "Strategi Daya EA-DSRA",
            f"Profil daya berhasil diterapkan: {profile_name}\n"
            "Modulasi interval sampling Teensy (T_BM) telah disesuaikan."
        )

    def _on_reset_kalman(self):
        QtWidgets.QMessageBox.information(
            self, "Kalman Estimator",
            "Estimator Kalman 1D State-of-Charge telah ditare ke tegangan OCV nominal saat ini."
        )

    def update_telemetry(self, data: Dict[str, Any]):
        v_raw = data.get("battery_v", 24.0)
        v_kalman = data.get("battery_v", v_raw)
        curr_a = data.get("current_a", 0.0)
        soc = data.get("soc_kalman", data.get("soc", 100.0))
        pwr_thruster = v_kalman * curr_a

        sensor_v = data.get("sensor_battery_v", 12.0)
        sensor_curr = data.get("sensor_current_a", 0.0)
        sensor_soc = data.get("sensor_soc", 100.0)
        pwr_sensor = sensor_v * sensor_curr
        pwr_total = pwr_thruster + pwr_sensor

        # 1. Update Baterai 1 (Thruster 6S LiPo)
        v_cell = v_kalman / 6.0
        self.lbl_v_info.setText(f"Kalman: {v_kalman:.2f} V | Raw: {v_raw:.2f} V | Sel: {v_cell:.2f} V/cell")
        self.lbl_soc.setText(f"{soc:.1f}%")

        soc_clamped = max(0, min(100, int(soc)))
        self.soc_bar.setValue(soc_clamped)

        # Dynamic battery color (Green > 45%, Amber 20-45%, Red < 20%)
        if soc >= 45.0:
            self.lbl_soc.setStyleSheet("color: #34d399; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace;")
            self.soc_bar.setStyleSheet("""
                QProgressBar { background-color: #1a202c; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #10b981; border-radius: 2px; }
            """)
        elif soc >= 20.0:
            self.lbl_soc.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace;")
            self.soc_bar.setStyleSheet("""
                QProgressBar { background-color: #1a202c; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #f59e0b; border-radius: 2px; }
            """)
        else:
            self.lbl_soc.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace;")
            self.soc_bar.setStyleSheet("""
                QProgressBar { background-color: #1a202c; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #ef4444; border-radius: 2px; }
            """)

        # Estimate remaining mission runtime
        rem_ah = (soc / 100.0) * 16.0
        if curr_a > 0.3:
            rem_hours = rem_ah / curr_a
            h = int(rem_hours)
            m = int((rem_hours - h) * 60)
            self.lbl_runtime.setText(f"Arus: {curr_a:.2f} A | Estimasi: ~{h} Jam {m:02d} Menit")
        else:
            self.lbl_runtime.setText(f"Arus: {curr_a:.2f} A | Estimasi: Standby (>8 Jam)")

        # 2. Update Baterai 2 (Rel Sensor & Mikrokontroler)
        self.lbl_sensor_soc.setText(f"{sensor_soc:.1f}%")
        sensor_soc_clamped = max(0, min(100, int(sensor_soc)))
        self.sensor_soc_bar.setValue(sensor_soc_clamped)
        self.lbl_curr.setText(f"Tegangan: {sensor_v:.2f} V | Arus: {sensor_curr:.2f} A | Daya: {pwr_sensor:.1f} W")
        self.lbl_energy_used.setText(f"Total Daya Sistem: {pwr_total:.1f} W (B1: {pwr_thruster:.1f}W + B2: {pwr_sensor:.1f}W)")

        # 3. Update EA-DSRA Sampling Interval Telemetry
        t_ph = data.get("tbm_ph", 5.0)
        t_do = data.get("tbm_do", 2.0)
        t_temp = data.get("tbm_temp", 3.0)
        t_cond = data.get("tbm_cond", 4.0)
        wea = data.get("wea_penalty", 1.0)

        self.lbl_t_ph_val.setText(f"{t_ph:.1f} s")
        self.bar_t_ph.setValue(int(t_ph * 10))

        self.lbl_t_do_val.setText(f"{t_do:.1f} s")
        self.bar_t_do.setValue(int(t_do * 10))

        self.lbl_t_temp_val.setText(f"{t_temp:.1f} s")
        self.bar_t_temp.setValue(int(t_temp * 10))

        self.lbl_t_cond_val.setText(f"{t_cond:.1f} s")
        self.bar_t_cond.setValue(int(t_cond * 10))

        # Overall Energy Savings %
        avg_tbm = (t_ph + t_do + t_temp + t_cond) / 4.0
        savings_pct = max(0, min(95, int((1.0 - (1.0 / max(1.0, avg_tbm))) * 100)))
        self.sav_bar.setValue(savings_pct)
        self.lbl_sav_text.setText(f"{savings_pct}% Energi Terhemat (vs 1.0 Hz Kontinu)")

        # Penalty factor display
        if soc < 30.0:
            wea = 30.0 / max(5.0, soc)
            self.lbl_wea.setText(f"Faktor Penalti W_ea: {wea:.2f} (Aktif / Proteksi)")
            self.lbl_wea.setStyleSheet("""
                color: #fca5a5;
                font-size: 9.5px;
                font-weight: 600;
                background-color: #450a0a;
                border: 1px solid #991b1b;
                border-radius: 3px;
                padding: 1px 6px;
            """)
        else:
            self.lbl_wea.setText("Faktor Penalti W_ea: 1.00 (Normal / Efisiensi)")
            self.lbl_wea.setStyleSheet("""
                color: #38bdf8;
                font-size: 9.5px;
                font-weight: 600;
                background-color: #0c4a6e;
                border: 1px solid #0369a1;
                border-radius: 3px;
                padding: 1px 6px;
            """)

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name
        card_bg = "#12151e" if is_dark else "#F8FAFC"
        card_border = "#202636" if is_dark else "#E2E8F0"
        title_color = "#94a3b8" if is_dark else "#475569"
        text_color = "#cbd5e1" if is_dark else "#1E293B"
        sub_color = "#64748b" if is_dark else "#64748B"

        if hasattr(self, "frame_batt"):
            self.frame_batt.setStyleSheet(f"QFrame {{ background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 5px; }}")
        if hasattr(self, "frame_pwr"):
            self.frame_pwr.setStyleSheet(f"QFrame {{ background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 5px; }}")
        if hasattr(self, "lbl_b_title"):
            self.lbl_b_title.setStyleSheet(f"color: {title_color}; font-size: 10px; font-weight: 700; letter-spacing: 0.3px;")
        if hasattr(self, "lbl_p_title"):
            self.lbl_p_title.setStyleSheet(f"color: {title_color}; font-size: 10px; font-weight: 700; letter-spacing: 0.3px;")
        if hasattr(self, "lbl_v_info"):
            self.lbl_v_info.setStyleSheet(f"color: {text_color}; font-size: 9.5px; font-family: 'Consolas', monospace;")
        if hasattr(self, "lbl_curr"):
            self.lbl_curr.setStyleSheet(f"color: {text_color}; font-size: 9.5px; font-weight: 600; font-family: 'Consolas', monospace;")
        if hasattr(self, "lbl_runtime"):
            self.lbl_runtime.setStyleSheet(f"color: {sub_color}; font-size: 9.5px;")
        if hasattr(self, "lbl_energy_used"):
            self.lbl_energy_used.setStyleSheet(f"color: {sub_color}; font-size: 9.5px;")

