# -*- coding: utf-8 -*-
"""
02 Kontrol & Misi Tab
Redesigned to strictly adhere to Charisto's Tyrant-AQ GCS PRD & Web Mockup specifications:
  1. Kendali Manual Panel:
     - Input source selector (Keyboard laptop / Controller)
     - Deadman spacebar indicator & manual meter axes (Surge, Sway, Heave, Yaw)
     - Input scale slider (default 40%)
  2. Referensi & Target Panel:
     - Yaw mission reference switch & magnetometer heading offset
     - Target depth & heading inputs
     - Actions: Terapkan target, Naik ke permukaan, Set Surface / nol
  3. Mission Planner Panel:
     - Plan settings: Daya sensor (throughout/at_point), depth tolerance, settling window, sample count
     - Multi-column step table (WAIT, SURGE, SWAY, DIVE, HEADING, SURFACE) with Effort, Timeout,
       Tolerance, Sampling checkbox, Timing (during/after), and dynamic step reordering (Up/Down/Delete).
"""
from typing import Dict, Any, List, Optional
from PyQt5 import QtWidgets, QtCore, QtGui


CLR_BG_CARD = "#161922"
CLR_BORDER = "#252B3B"
CLR_ACCENT = "#1976D2"
CLR_ACCENT_HOVER = "#2196F3"
CLR_DANGER = "#C62828"
CLR_DANGER_HOVER = "#E53935"
CLR_TEXT = "#E0E0E0"
CLR_MUTED = "#90A4AE"
CLR_SUCCESS = "#2E7D32"


class MissionControl(QtWidgets.QWidget):
    """
    Tab 2: 02 Kontrol & Misi
    Implements Kendali Manual, Referensi & Target, and Tactical Mission Planner.
    """
    command_generated = QtCore.pyqtSignal(str)
    manual_scale_changed = QtCore.pyqtSignal(float)
    yaw_reference_changed = QtCore.pyqtSignal(bool, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_depth = 0.0
        self.current_yaw = 0.0
        self.mission_active = False
        self.current_step_index = -1

        # Fallback/Backward-compatibility stubs for config manager
        self.sp_np = QtWidgets.QSpinBox()
        self.sp_nc = QtWidgets.QSpinBox()
        self.sp_qz = QtWidgets.QDoubleSpinBox()
        self.sp_r = QtWidgets.QDoubleSpinBox()
        self.sp_soc_th = QtWidgets.QDoubleSpinBox()
        self.sp_ph_e = QtWidgets.QDoubleSpinBox()
        self.sp_ph_s = QtWidgets.QSpinBox()

        self.init_ui()
        self._load_default_plan()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Scroll area for smaller screens/tablets
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # =========================================================
        # BARIS 1: KENDALI MANUAL & REFERENSI TARGET (2 KOLOM)
        # =========================================================
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)

        # ---------------------------------------------------------
        # 1. KENDALI MANUAL
        # ---------------------------------------------------------
        grp_manual = QtWidgets.QGroupBox()
        grp_manual_layout = QtWidgets.QVBoxLayout(grp_manual)
        grp_manual_layout.setContentsMargins(10, 10, 10, 10)
        grp_manual_layout.setSpacing(6)

        header_manual = QtWidgets.QHBoxLayout()
        lbl_manual_title = QtWidgets.QLabel("KENDALI MANUAL")
        lbl_manual_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #58A6FF;")
        header_manual.addWidget(lbl_manual_title)
        header_manual.addStretch(1)
        self.badge_manual_mode = QtWidgets.QLabel("MANUAL")
        self.badge_manual_mode.setStyleSheet(
            "background-color: #21262D; color: #58A6FF; border: 1px solid #30363D; "
            "border-radius: 3px; padding: 1px 6px; font-size: 9px; font-weight: bold;"
        )
        header_manual.addWidget(self.badge_manual_mode)
        grp_manual_layout.addLayout(header_manual)

        # Sumber input
        row_src = QtWidgets.QHBoxLayout()
        row_src.addWidget(QtWidgets.QLabel("Sumber input:"))
        self.combo_input_source = QtWidgets.QComboBox()
        self.combo_input_source.addItems(["Keyboard laptop", "Controller laptop / HP"])
        self.combo_input_source.currentIndexChanged.connect(self._on_input_source_changed)
        row_src.addWidget(self.combo_input_source, stretch=1)
        grp_manual_layout.addLayout(row_src)

        self.lbl_input_help = QtWidgets.QLabel("W/S maju · A/D geser · Q/E yaw · R/F vertikal")
        self.lbl_input_help.setStyleSheet("color: #8B949E; font-size: 10px;")
        grp_manual_layout.addWidget(self.lbl_input_help)

        # Manual meter card
        frame_meter = QtWidgets.QFrame()
        frame_meter.setStyleSheet("background-color: #0D1117; border: 1px solid #21262D; border-radius: 4px; padding: 6px;")
        f_layout = QtWidgets.QVBoxLayout(frame_meter)
        f_layout.setContentsMargins(6, 4, 6, 4)
        f_layout.setSpacing(3)
        self.lbl_manual_status = QtWidgets.QLabel("Pilih MANUAL, lalu tahan Space")
        self.lbl_manual_status.setStyleSheet("color: #C9D1D9; font-size: 10px; font-weight: 500;")
        self.lbl_manual_axes = QtWidgets.QLabel("Surge 0.00 · Sway 0.00 · Heave 0.00 · Yaw 0.00")
        self.lbl_manual_axes.setStyleSheet("color: #58A6FF; font-size: 11px; font-weight: bold;")
        f_layout.addWidget(self.lbl_manual_status)
        f_layout.addWidget(self.lbl_manual_axes)
        grp_manual_layout.addWidget(frame_meter)

        # Skala input manual
        row_scale = QtWidgets.QHBoxLayout()
        row_scale.addWidget(QtWidgets.QLabel("Skala input manual:"))
        self.lbl_scale_val = QtWidgets.QLabel("40%")
        self.lbl_scale_val.setStyleSheet("font-weight: bold; color: #58A6FF;")
        row_scale.addStretch(1)
        row_scale.addWidget(self.lbl_scale_val)
        grp_manual_layout.addLayout(row_scale)

        self.slider_scale = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_scale.setRange(0, 100)
        self.slider_scale.setValue(40)
        self.slider_scale.valueChanged.connect(self._on_scale_changed)
        grp_manual_layout.addWidget(self.slider_scale)

        lbl_manual_foot = QtWidgets.QLabel("Space = deadman. Lepas/fokus hilang = netral. Tidak mengirim gerak tanpa deadman.")
        lbl_manual_foot.setWordWrap(True)
        lbl_manual_foot.setStyleSheet("color: #8B949E; font-size: 9px;")
        grp_manual_layout.addWidget(lbl_manual_foot)

        self.lbl_gamepad_state = QtWidgets.QLabel("Controller: pemeriksaan input saja")
        self.lbl_gamepad_state.setStyleSheet("color: #8B949E; font-size: 9px; font-style: italic;")
        grp_manual_layout.addWidget(self.lbl_gamepad_state)

        top_row.addWidget(grp_manual, stretch=1)

        # ---------------------------------------------------------
        # 2. REFERENSI & TARGET
        # ---------------------------------------------------------
        grp_target = QtWidgets.QGroupBox()
        grp_target_layout = QtWidgets.QVBoxLayout(grp_target)
        grp_target_layout.setContentsMargins(10, 10, 10, 10)
        grp_target_layout.setSpacing(6)

        header_target = QtWidgets.QHBoxLayout()
        lbl_target_title = QtWidgets.QLabel("REFERENSI & TARGET")
        lbl_target_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #58A6FF;")
        header_target.addWidget(lbl_target_title)
        header_target.addStretch(1)

        self.btn_ref_help = QtWidgets.QPushButton("?")
        self.btn_ref_help.setFixedSize(20, 20)
        self.btn_ref_help.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_ref_help.setStyleSheet(
            "background-color: #21262D; color: #8B949E; border: 1px solid #30363D; "
            "border-radius: 10px; font-weight: bold; font-size: 10px;"
        )
        self.btn_ref_help.clicked.connect(self._toggle_ref_help)
        header_target.addWidget(self.btn_ref_help)
        grp_target_layout.addLayout(header_target)

        # Collapsible Help Box
        self.frame_ref_help = QtWidgets.QFrame()
        self.frame_ref_help.setVisible(False)
        self.frame_ref_help.setStyleSheet(
            "background-color: #0D1117; border: 1px solid #30363D; border-radius: 4px; padding: 6px;"
        )
        help_layout = QtWidgets.QVBoxLayout(self.frame_ref_help)
        help_layout.setContentsMargins(6, 4, 6, 4)
        help_layout.setSpacing(4)
        help_text = QtWidgets.QLabel(
            "• <b>Set Surface:</b> Menetapkan nol tekanan di permukaan saat IDLE.<br>"
            "• <b>Referensi Yaw:</b> Heading asli tetap disimpan. Jika arah sekarang (misal 37°) "
            "dijadikan 0°, target relatif 90° dikonversi otomatis ke heading asli 127°.<br>"
            "• Referensi dikunci selama misi aktif."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #C9D1D9; font-size: 10px;")
        help_layout.addWidget(help_text)
        grp_target_layout.addWidget(self.frame_ref_help)

        # Yaw Reference Options
        row_yaw_cb = QtWidgets.QHBoxLayout()
        self.cb_yaw_ref = QtWidgets.QCheckBox("Gunakan nol yaw misi")
        self.cb_yaw_ref.setStyleSheet("font-weight: 500; font-size: 10px;")
        self.cb_yaw_ref.toggled.connect(self._on_yaw_ref_toggled)
        row_yaw_cb.addWidget(self.cb_yaw_ref)
        grp_target_layout.addLayout(row_yaw_cb)

        row_yaw_fields = QtWidgets.QHBoxLayout()
        row_yaw_fields.setSpacing(6)
        row_yaw_fields.addWidget(QtWidgets.QLabel("Heading nol (°):"))
        self.sp_yaw_offset = QtWidgets.QDoubleSpinBox()
        self.sp_yaw_offset.setRange(0.0, 359.99)
        self.sp_yaw_offset.setValue(0.0)
        self.sp_yaw_offset.setEnabled(False)
        self.sp_yaw_offset.valueChanged.connect(self._on_yaw_offset_changed)
        row_yaw_fields.addWidget(self.sp_yaw_offset)

        self.btn_zero_current_yaw = QtWidgets.QPushButton("Arah skrg = 0°")
        self.btn_zero_current_yaw.setEnabled(False)
        self.btn_zero_current_yaw.setStyleSheet("padding: 3px 8px; font-size: 10px;")
        self.btn_zero_current_yaw.clicked.connect(self._set_current_yaw_as_zero)
        row_yaw_fields.addWidget(self.btn_zero_current_yaw)
        grp_target_layout.addLayout(row_yaw_fields)

        self.lbl_yaw_summary = QtWidgets.QLabel("Default: heading asli magnetometer")
        self.lbl_yaw_summary.setStyleSheet("color: #8B949E; font-size: 9px;")
        grp_target_layout.addWidget(self.lbl_yaw_summary)

        # Target Depth & Target Heading Inputs
        grid_target = QtWidgets.QGridLayout()
        grid_target.setHorizontalSpacing(8)
        grid_target.setVerticalSpacing(4)

        grid_target.addWidget(QtWidgets.QLabel("Target depth (m):"), 0, 0)
        self.sp_target_depth = QtWidgets.QDoubleSpinBox()
        self.sp_target_depth.setRange(0.0, 10.0)
        self.sp_target_depth.setSingleStep(0.1)
        self.sp_target_depth.setValue(1.0)
        grid_target.addWidget(self.sp_target_depth, 0, 1)

        self.lbl_target_heading = QtWidgets.QLabel("Heading asli (°):")
        grid_target.addWidget(self.lbl_target_heading, 1, 0)
        self.sp_target_heading = QtWidgets.QSpinBox()
        self.sp_target_heading.setRange(0, 359)
        self.sp_target_heading.setValue(90)
        grid_target.addWidget(self.sp_target_heading, 1, 1)

        grp_target_layout.addLayout(grid_target)

        # Action buttons
        row_actions = QtWidgets.QHBoxLayout()
        row_actions.setSpacing(6)

        self.btn_apply_target = QtWidgets.QPushButton("Terapkan target")
        self.btn_apply_target.setStyleSheet(
            "background-color: #1976D2; color: white; font-weight: bold; padding: 5px 8px; border-radius: 3px;"
        )
        self.btn_apply_target.clicked.connect(self.on_apply_target)
        row_actions.addWidget(self.btn_apply_target)

        self.btn_surface = QtWidgets.QPushButton("Naik permukaan")
        self.btn_surface.setStyleSheet("padding: 5px 8px;")
        self.btn_surface.clicked.connect(self.on_surface_command)
        row_actions.addWidget(self.btn_surface)

        self.btn_zero_depth = QtWidgets.QPushButton("Set Surface / nol")
        self.btn_zero_depth.setStyleSheet("padding: 5px 8px;")
        self.btn_zero_depth.clicked.connect(self.on_zero_depth_calibration)
        row_actions.addWidget(self.btn_zero_depth)

        grp_target_layout.addLayout(row_actions)

        lbl_target_foot = QtWidgets.QLabel("Set Surface adalah kalibrasi nol saat IDLE. Target depth berlaku pada mode auto/depth hold.")
        lbl_target_foot.setWordWrap(True)
        lbl_target_foot.setStyleSheet("color: #8B949E; font-size: 9px;")
        grp_target_layout.addWidget(lbl_target_foot)

        top_row.addWidget(grp_target, stretch=1)
        layout.addLayout(top_row)

        # =========================================================
        # BARIS 2: MISSION PLANNER (FULL WIDTH TABEL & SETTINGS)
        # =========================================================
        grp_planner = QtWidgets.QGroupBox()
        grp_planner_layout = QtWidgets.QVBoxLayout(grp_planner)
        grp_planner_layout.setContentsMargins(10, 10, 10, 10)
        grp_planner_layout.setSpacing(8)

        # Header Planner
        header_planner = QtWidgets.QHBoxLayout()
        header_planner_info = QtWidgets.QVBoxLayout()
        lbl_planner_title = QtWidgets.QLabel("MISSION PLANNER")
        lbl_planner_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #58A6FF;")
        lbl_planner_sub = QtWidgets.QLabel("Lintasan rencana · tanpa estimasi posisi XY · urutan langkah sekuensial")
        lbl_planner_sub.setStyleSheet("color: #8B949E; font-size: 10px;")
        header_planner_info.addWidget(lbl_planner_title)
        header_planner_info.addWidget(lbl_planner_sub)
        header_planner.addLayout(header_planner_info)
        header_planner.addStretch(1)

        self.lbl_mission_badge = QtWidgets.QLabel("IDLE")
        self.lbl_mission_badge.setStyleSheet(
            "background-color: #21262D; color: #8B949E; border: 1px solid #30363D; "
            "border-radius: 4px; padding: 2px 10px; font-weight: bold; font-size: 10px;"
        )
        header_planner.addWidget(self.lbl_mission_badge)
        grp_planner_layout.addLayout(header_planner)

        # Plan Settings (4 parameter cards)
        row_settings = QtWidgets.QHBoxLayout()
        row_settings.setSpacing(10)

        # 1. Daya sensor
        col_s1 = QtWidgets.QVBoxLayout()
        col_s1.addWidget(QtWidgets.QLabel("Daya sensor:"))
        self.combo_sampling_policy = QtWidgets.QComboBox()
        self.combo_sampling_policy.addItems(["Sepanjang perjalanan", "Hanya di titik sampling"])
        col_s1.addWidget(self.combo_sampling_policy)
        row_settings.addLayout(col_s1)

        # 2. Toleransi depth
        col_s2 = QtWidgets.QVBoxLayout()
        col_s2.addWidget(QtWidgets.QLabel("Toleransi depth (± m):"))
        self.sp_depth_tol = QtWidgets.QDoubleSpinBox()
        self.sp_depth_tol.setRange(0.01, 2.00)
        self.sp_depth_tol.setSingleStep(0.05)
        self.sp_depth_tol.setValue(0.20)
        col_s2.addWidget(self.sp_depth_tol)
        row_settings.addLayout(col_s2)

        # 3. Jendela penanda stabil
        col_s3 = QtWidgets.QVBoxLayout()
        col_s3.addWidget(QtWidgets.QLabel("Jendela stabil (s):"))
        self.sp_stable_window = QtWidgets.QSpinBox()
        self.sp_stable_window.setRange(1, 30)
        self.sp_stable_window.setValue(3)
        col_s3.addWidget(self.sp_stable_window)
        row_settings.addLayout(col_s3)

        # 4. Sampel per sensor
        col_s4 = QtWidgets.QVBoxLayout()
        col_s4.addWidget(QtWidgets.QLabel("Sampel / sensor:"))
        self.sp_sample_count = QtWidgets.QSpinBox()
        self.sp_sample_count.setRange(1, 50)
        self.sp_sample_count.setValue(3)
        col_s4.addWidget(self.sp_sample_count)
        row_settings.addLayout(col_s4)

        grp_planner_layout.addLayout(row_settings)

        # Table Steps
        self.table_steps = QtWidgets.QTableWidget(0, 9)
        self.table_steps.setHorizontalHeaderLabels([
            "#", "Jenis", "Target / Durasi", "Effort (%)", "Timeout (s)", "Toleransi", "Sampling", "Waktu Sampel", "Aksi"
        ])
        self.table_steps.horizontalHeader().setStretchLastSection(False)
        self.table_steps.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table_steps.verticalHeader().setVisible(False)
        self.table_steps.setMinimumHeight(200)
        self.table_steps.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117;
                border: 1px solid #21262D;
                gridline-color: #161B22;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #161B22;
                color: #C9D1D9;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid #21262D;
                padding: 4px;
            }
        """)
        grp_planner_layout.addWidget(self.table_steps)

        # Planner bottom row (Buttons & Progress)
        row_planner_bottom = QtWidgets.QHBoxLayout()
        row_planner_bottom.setSpacing(8)

        self.btn_add_step = QtWidgets.QPushButton("+ Tambah langkah")
        self.btn_add_step.setStyleSheet("padding: 6px 12px; font-weight: bold;")
        self.btn_add_step.clicked.connect(self._add_step_default)
        row_planner_bottom.addWidget(self.btn_add_step)

        self.btn_start_mission = QtWidgets.QPushButton("Mulai misi otonom")
        self.btn_start_mission.setStyleSheet(
            "background-color: #1976D2; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        self.btn_start_mission.clicked.connect(self.on_start_mission)
        row_planner_bottom.addWidget(self.btn_start_mission)

        self.btn_abort_mission = QtWidgets.QPushButton("Batalkan / Stop misi")
        self.btn_abort_mission.setStyleSheet(
            "background-color: #C62828; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        self.btn_abort_mission.clicked.connect(self.on_abort_mission)
        row_planner_bottom.addWidget(self.btn_abort_mission)

        row_planner_bottom.addStretch(1)

        self.lbl_mission_progress = QtWidgets.QLabel("Belum ada misi aktif")
        self.lbl_mission_progress.setStyleSheet("color: #8B949E; font-size: 11px;")
        row_planner_bottom.addWidget(self.lbl_mission_progress)

        grp_planner_layout.addLayout(row_planner_bottom)

        lbl_planner_foot = QtWidgets.QLabel(
            "Sampling dapat diaktifkan pada semua jenis langkah, selama gerak atau setelah selesai. "
            "Depth berubah tetap dicatat dengan penanda. Pilih AUTO di bar atas untuk mengeksekusi misi rencana."
        )
        lbl_planner_foot.setWordWrap(True)
        lbl_planner_foot.setStyleSheet("color: #8B949E; font-size: 9px;")
        grp_planner_layout.addWidget(lbl_planner_foot)

        layout.addWidget(grp_planner)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    # =========================================================
    # --- DEFAULT PLAN & STEP MANAGEMENT ---
    # =========================================================
    def _load_default_plan(self):
        """Loads default 5-step plan from Charisto's specification."""
        self.table_steps.setRowCount(0)
        default_steps = [
            {"type": "DIVE", "value": 1.0, "effort": 35, "timeout": 45.0, "tolerance": 0.20, "sampling": True, "timing": "Selama langkah"},
            {"type": "SURGE", "value": 10.0, "effort": 35, "timeout": 20.0, "tolerance": 0.0, "sampling": False, "timing": "Selama langkah"},
            {"type": "SWAY", "value": 5.0, "effort": 35, "timeout": 15.0, "tolerance": 0.0, "sampling": False, "timing": "Selama langkah"},
            {"type": "HEADING", "value": 90.0, "effort": 35, "timeout": 45.0, "tolerance": 5.0, "sampling": False, "timing": "Selama langkah"},
            {"type": "DIVE", "value": 3.0, "effort": 35, "timeout": 45.0, "tolerance": 0.20, "sampling": True, "timing": "Selama langkah"},
        ]
        for s in default_steps:
            self._insert_step_row(s)

    def _add_step_default(self):
        default_step = {
            "type": "WAIT", "value": 5.0, "effort": 0, "timeout": 15.0, "tolerance": 0.0, "sampling": False, "timing": "Selama langkah"
        }
        self._insert_step_row(default_step)

    def _insert_step_row(self, step_data: dict, index: Optional[int] = None):
        row = self.table_steps.rowCount() if index is None else index
        self.table_steps.insertRow(row)

        # Col 0: Index (#)
        item_idx = QtWidgets.QTableWidgetItem(f"{row + 1:02d}")
        item_idx.setTextAlignment(QtCore.Qt.AlignCenter)
        item_idx.setFlags(QtCore.Qt.ItemIsEnabled)
        self.table_steps.setItem(row, 0, item_idx)

        # Col 1: Jenis (WAIT, SURGE, SWAY, DIVE, HEADING, SURFACE)
        combo_type = QtWidgets.QComboBox()
        combo_type.addItems(["WAIT", "SURGE", "SWAY", "DIVE", "HEADING", "SURFACE"])
        combo_type.setCurrentText(step_data.get("type", "WAIT"))
        self.table_steps.setCellWidget(row, 1, combo_type)

        # Col 2: Target / Durasi
        sp_val = QtWidgets.QDoubleSpinBox()
        sp_val.setRange(0.0, 3600.0)
        sp_val.setValue(float(step_data.get("value", 5.0)))
        self.table_steps.setCellWidget(row, 2, sp_val)

        # Col 3: Effort (%)
        sp_effort = QtWidgets.QSpinBox()
        sp_effort.setRange(-100, 100)
        sp_effort.setValue(int(step_data.get("effort", 35)))
        self.table_steps.setCellWidget(row, 3, sp_effort)

        # Col 4: Timeout (s)
        sp_timeout = QtWidgets.QDoubleSpinBox()
        sp_timeout.setRange(0.1, 3600.0)
        sp_timeout.setValue(float(step_data.get("timeout", 45.0)))
        self.table_steps.setCellWidget(row, 4, sp_timeout)

        # Col 5: Toleransi
        sp_tol = QtWidgets.QDoubleSpinBox()
        sp_tol.setRange(0.0, 180.0)
        sp_tol.setValue(float(step_data.get("tolerance", 0.20)))
        self.table_steps.setCellWidget(row, 5, sp_tol)

        # Col 6: Sampling (Checkbox)
        cb_samp = QtWidgets.QCheckBox("Sampel")
        cb_samp.setChecked(bool(step_data.get("sampling", False)))
        w_samp = QtWidgets.QWidget()
        l_samp = QtWidgets.QHBoxLayout(w_samp)
        l_samp.setContentsMargins(4, 2, 4, 2)
        l_samp.setAlignment(QtCore.Qt.AlignCenter)
        l_samp.addWidget(cb_samp)
        self.table_steps.setCellWidget(row, 6, w_samp)

        # Col 7: Waktu Sampel (Selama langkah / Setelah selesai)
        combo_timing = QtWidgets.QComboBox()
        combo_timing.addItems(["Selama langkah", "Setelah selesai"])
        combo_timing.setCurrentText(step_data.get("timing", "Selama langkah"))
        combo_timing.setEnabled(cb_samp.isChecked())
        cb_samp.toggled.connect(combo_timing.setEnabled)
        self.table_steps.setCellWidget(row, 7, combo_timing)

        # Dynamic suffix & limits depending on step type
        def update_type_limits():
            t = combo_type.currentText()
            if t in ("DIVE", "SURFACE"):
                sp_val.setSuffix(" m")
                sp_val.setMaximum(10.0)
                sp_tol.setSuffix(" m")
                sp_tol.setEnabled(True)
                sp_effort.setEnabled(True)
            elif t == "HEADING":
                sp_val.setSuffix(" °")
                sp_val.setMaximum(359.0)
                sp_tol.setSuffix(" °")
                sp_tol.setEnabled(True)
                sp_effort.setEnabled(True)
            elif t == "WAIT":
                sp_val.setSuffix(" s")
                sp_val.setMaximum(600.0)
                sp_tol.setSuffix("")
                sp_tol.setEnabled(False)
                sp_effort.setEnabled(False)
                sp_effort.setValue(0)
            else:  # SURGE / SWAY
                sp_val.setSuffix(" s")
                sp_val.setMaximum(600.0)
                sp_tol.setSuffix("")
                sp_tol.setEnabled(False)
                sp_effort.setEnabled(True)

        combo_type.currentIndexChanged.connect(lambda: update_type_limits())
        update_type_limits()

        # Col 8: Action Buttons (Up, Down, Delete)
        w_actions = QtWidgets.QWidget()
        l_actions = QtWidgets.QHBoxLayout(w_actions)
        l_actions.setContentsMargins(2, 2, 2, 2)
        l_actions.setSpacing(2)

        btn_up = QtWidgets.QPushButton("↑")
        btn_up.setFixedSize(20, 20)
        btn_up.clicked.connect(lambda _, r=row: self._move_step(r, -1))
        l_actions.addWidget(btn_up)

        btn_down = QtWidgets.QPushButton("↓")
        btn_down.setFixedSize(20, 20)
        btn_down.clicked.connect(lambda _, r=row: self._move_step(r, 1))
        l_actions.addWidget(btn_down)

        btn_del = QtWidgets.QPushButton("×")
        btn_del.setFixedSize(20, 20)
        btn_del.setStyleSheet("color: #F85149; font-weight: bold;")
        btn_del.clicked.connect(lambda _, r=row: self._delete_step(r))
        l_actions.addWidget(btn_del)

        self.table_steps.setCellWidget(row, 8, w_actions)
        self._refresh_indices()

    def _refresh_indices(self):
        """Renumber row indices and rebind action handlers."""
        for r in range(self.table_steps.rowCount()):
            item = self.table_steps.item(r, 0)
            if item:
                item.setText(f"{r + 1:02d}")
            w = self.table_steps.cellWidget(r, 8)
            if w:
                buttons = w.findChildren(QtWidgets.QPushButton)
                if len(buttons) >= 3:
                    btn_up, btn_down, btn_del = buttons[0], buttons[1], buttons[2]
                    btn_up.setEnabled(r > 0)
                    btn_down.setEnabled(r < self.table_steps.rowCount() - 1)
                    btn_up.disconnect()
                    btn_down.disconnect()
                    btn_del.disconnect()
                    btn_up.clicked.connect(lambda _, curr_r=r: self._move_step(curr_r, -1))
                    btn_down.clicked.connect(lambda _, curr_r=r: self._move_step(curr_r, 1))
                    btn_del.clicked.connect(lambda _, curr_r=r: self._delete_step(curr_r))

    def _move_step(self, row: int, direction: int):
        new_row = row + direction
        if 0 <= new_row < self.table_steps.rowCount():
            step_a = self._extract_step_dict(row)
            step_b = self._extract_step_dict(new_row)
            self._apply_step_dict(row, step_b)
            self._apply_step_dict(new_row, step_a)

    def _delete_step(self, row: int):
        if self.table_steps.rowCount() > 1:
            self.table_steps.removeRow(row)
            self._refresh_indices()
        else:
            QtWidgets.QMessageBox.warning(self, "Hapus Langkah", "Rencana misi harus memiliki minimal satu langkah.")

    def _extract_step_dict(self, row: int) -> dict:
        combo_type = self.table_steps.cellWidget(row, 1)
        sp_val = self.table_steps.cellWidget(row, 2)
        sp_effort = self.table_steps.cellWidget(row, 3)
        sp_timeout = self.table_steps.cellWidget(row, 4)
        sp_tol = self.table_steps.cellWidget(row, 5)
        w_samp = self.table_steps.cellWidget(row, 6)
        cb_samp = w_samp.findChild(QtWidgets.QCheckBox) if w_samp else None
        combo_timing = self.table_steps.cellWidget(row, 7)

        return {
            "type": combo_type.currentText() if combo_type else "WAIT",
            "value": sp_val.value() if sp_val else 0.0,
            "effort": sp_effort.value() if sp_effort else 0,
            "timeout": sp_timeout.value() if sp_timeout else 10.0,
            "tolerance": sp_tol.value() if sp_tol else 0.2,
            "sampling": cb_samp.isChecked() if cb_samp else False,
            "timing": combo_timing.currentText() if combo_timing else "Selama langkah"
        }

    def _apply_step_dict(self, row: int, data: dict):
        combo_type = self.table_steps.cellWidget(row, 1)
        sp_val = self.table_steps.cellWidget(row, 2)
        sp_effort = self.table_steps.cellWidget(row, 3)
        sp_timeout = self.table_steps.cellWidget(row, 4)
        sp_tol = self.table_steps.cellWidget(row, 5)
        w_samp = self.table_steps.cellWidget(row, 6)
        cb_samp = w_samp.findChild(QtWidgets.QCheckBox) if w_samp else None
        combo_timing = self.table_steps.cellWidget(row, 7)

        if combo_type:
            combo_type.setCurrentText(data.get("type", "WAIT"))
        if sp_val:
            sp_val.setValue(data.get("value", 0.0))
        if sp_effort:
            sp_effort.setValue(data.get("effort", 0))
        if sp_timeout:
            sp_timeout.setValue(data.get("timeout", 10.0))
        if sp_tol:
            sp_tol.setValue(data.get("tolerance", 0.2))
        if cb_samp:
            cb_samp.setChecked(data.get("sampling", False))
        if combo_timing:
            combo_timing.setCurrentText(data.get("timing", "Selama langkah"))

    # =========================================================
    # --- EVENT HANDLERS: MANUAL & REFERENCE TARGET ---
    # =========================================================
    def _on_input_source_changed(self, index: int):
        if index == 0:
            self.lbl_input_help.setText("W/S maju · A/D geser · Q/E yaw · R/F vertikal")
            self.lbl_gamepad_state.setText("Controller: pemeriksaan input saja")
        else:
            self.lbl_input_help.setText("Pemeriksaan axes saja. Mapping/deadman browser belum dikualifikasi.")
            self.lbl_gamepad_state.setText("Controller: siap menerima input perangkat")

    def _on_scale_changed(self, val: int):
        self.lbl_scale_val.setText(f"{val}%")
        self.manual_scale_changed.emit(val / 100.0)

    def _toggle_ref_help(self):
        self.frame_ref_help.setVisible(not self.frame_ref_help.isVisible())

    def _on_yaw_ref_toggled(self, checked: bool):
        self.sp_yaw_offset.setEnabled(checked)
        self.btn_zero_current_yaw.setEnabled(checked)
        if checked:
            self.lbl_target_heading.setText("Heading target (°):")
            self.lbl_yaw_summary.setText(f"Offset yaw misi: {self.sp_yaw_offset.value():.1f}°")
        else:
            self.lbl_target_heading.setText("Heading asli (°):")
            self.lbl_yaw_summary.setText("Default: heading asli magnetometer")
        self.yaw_reference_changed.emit(checked, self.sp_yaw_offset.value())

    def _on_yaw_offset_changed(self, val: float):
        if self.cb_yaw_ref.isChecked():
            self.lbl_yaw_summary.setText(f"Offset yaw misi: {val:.1f}°")
            self.yaw_reference_changed.emit(True, val)

    def _set_current_yaw_as_zero(self):
        self.sp_yaw_offset.setValue(self.current_yaw)
        self.lbl_yaw_summary.setText(f"Arah sekarang {self.current_yaw:.1f}° dijadikan 0° misi")

    def on_apply_target(self):
        depth = self.sp_target_depth.value()
        heading = self.sp_target_heading.value()
        # Convert relative target heading to raw if yaw reference is enabled
        raw_heading = heading
        if self.cb_yaw_ref.isChecked():
            raw_heading = ((heading + self.sp_yaw_offset.value()) % 360.0)

        self.command_generated.emit(f"SETPOINT,{depth:.2f}\n")
        self.command_generated.emit(f"TARGET_YAW,{raw_heading:.1f}\n")
        self.lbl_mission_progress.setText(f"Target diterapkan: depth={depth:.2f} m, heading={raw_heading:.1f}°")

    def on_surface_command(self):
        self.command_generated.emit("SURFACE\n")
        self.command_generated.emit("SETPOINT,0.0\n")
        self.sp_target_depth.setValue(0.0)
        self.lbl_mission_progress.setText("Perintah: Naik ke permukaan (Depth 0.0 m)")

    def on_zero_depth_calibration(self):
        self.command_generated.emit("ZERO_DEPTH\n")
        self.lbl_mission_progress.setText("Kalibrasi nol tekanan permukaan (Set Surface) dikirim")

    # =========================================================
    # --- MISSION EXECUTION ---
    # =========================================================
    def on_start_mission(self):
        steps = []
        for r in range(self.table_steps.rowCount()):
            steps.append(self._extract_step_dict(r))

        if not steps:
            QtWidgets.QMessageBox.warning(self, "Misi Kosong", "Susun setidaknya satu langkah misi sebelum memulai.")
            return

        self.mission_active = True
        self.lbl_mission_badge.setText("ACTIVE")
        self.lbl_mission_badge.setStyleSheet(
            "background-color: #1976D2; color: #FFFFFF; border: 1px solid #0D47A1; "
            "border-radius: 4px; padding: 2px 10px; font-weight: bold; font-size: 10px;"
        )
        self.btn_start_mission.setEnabled(False)
        self.btn_abort_mission.setEnabled(True)

        # Notify backend & log
        summary = f"{len(steps)} Langkah ({steps[0]['type']} -> {steps[-1]['type']})"
        self.command_generated.emit(f"MISSION_START,{len(steps)}\n")
        self.lbl_mission_progress.setText(f"Misi otonom berjalan: {summary}")

    def on_abort_mission(self):
        self.mission_active = False
        self.lbl_mission_badge.setText("IDLE")
        self.lbl_mission_badge.setStyleSheet(
            "background-color: #21262D; color: #8B949E; border: 1px solid #30363D; "
            "border-radius: 4px; padding: 2px 10px; font-weight: bold; font-size: 10px;"
        )
        self.btn_start_mission.setEnabled(True)
        self.command_generated.emit("MISSION_STOP\n")
        self.lbl_mission_progress.setText("Misi dibatalkan oleh operator.")

    # =========================================================
    # --- TELEMETRY UPDATE ---
    # =========================================================
    def update_telemetry(self, data: Dict[str, Any]):
        self.current_depth = data.get("depth", 0.0)
        self.current_yaw = data.get("yaw", 0.0)

        # If manual inputs are reported, reflect in meter axes
        surge = data.get("manual_surge", 0.0)
        sway = data.get("manual_sway", 0.0)
        heave = data.get("manual_heave", 0.0)
        yaw = data.get("manual_yaw", 0.0)
        self.lbl_manual_axes.setText(
            f"Surge {surge:.2f} · Sway {sway:.2f} · Heave {heave:.2f} · Yaw {yaw:.2f}"
        )
