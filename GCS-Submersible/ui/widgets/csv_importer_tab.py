# -*- coding: utf-8 -*-
"""
CSV Importer & Offline Data Analyzer Tab
Allows users to load recorded CSV files, inspect data tables, and plot any columns without pandas dependency.
"""
import os
import csv
import datetime
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.exporters as pge


class ExportGraphDialog(QtWidgets.QDialog):
    """
    Dialog for configuring and exporting publication-ready chart images for documents.
    """
    def __init__(self, parent=None, active_cols=None):
        super().__init__(parent)
        self.setWindowTitle("Unduh Gambar Grafik untuk Dokumen")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.active_cols = active_cols or []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #14171C;
                color: #E6EDF3;
            }
            QGroupBox {
                border: 1px solid #30363D;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: bold;
                color: #58A6FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QRadioButton {
                color: #C9D1D9;
                font-size: 12px;
                spacing: 6px;
            }
            QRadioButton:hover {
                color: #58A6FF;
            }
            QPushButton {
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header description
        cols_text = ", ".join(self.active_cols) if self.active_cols else "Tidak ada"
        lbl_head = QtWidgets.QLabel(
            f"<b>Parameter Aktif:</b> <span style='color: #00E5FF;'>{cols_text}</span><br>"
            "Pilih format tema tampilan dan resolusi gambar sesuai kebutuhan dokumen Anda."
        )
        lbl_head.setStyleSheet("color: #C9D1D9; font-size: 11px;")
        lbl_head.setWordWrap(True)
        layout.addWidget(lbl_head)

        # Group 1: Tema Tampilan
        grp_theme = QtWidgets.QGroupBox("TEMA TAMPILAN GRAFIK")
        v_theme = QtWidgets.QVBoxLayout(grp_theme)
        v_theme.setSpacing(6)

        self.rb_white = QtWidgets.QRadioButton("📄 Format Dokumen / Publikasi (Latar Putih, Font Hitam)")
        self.rb_white.setChecked(True)
        self.rb_white.setStyleSheet("font-weight: bold; color: #FFFFFF;")

        lbl_sub_white = QtWidgets.QLabel("    Latar putih bersih standar laporan Word, PDF skripsi, atau jurnal.")
        lbl_sub_white.setStyleSheet("color: #8B949E; font-size: 11px;")

        self.rb_dark = QtWidgets.QRadioButton("🖥️ Format GUI Asli (Latar Gelap / Dark Mode)")
        self.rb_dark.setStyleSheet("font-weight: bold; color: #C9D1D9;")

        lbl_sub_dark = QtWidgets.QLabel("    Latar hitam industrial gelap sesuai tema GCS Submersible.")
        lbl_sub_dark.setStyleSheet("color: #8B949E; font-size: 11px;")

        v_theme.addWidget(self.rb_white)
        v_theme.addWidget(lbl_sub_white)
        v_theme.addSpacing(4)
        v_theme.addWidget(self.rb_dark)
        v_theme.addWidget(lbl_sub_dark)
        layout.addWidget(grp_theme)

        # Group 2: Resolusi Gambar
        grp_res = QtWidgets.QGroupBox("RESOLUSI GAMBAR")
        v_res = QtWidgets.QVBoxLayout(grp_res)
        v_res.setSpacing(6)

        self.rb_res_high = QtWidgets.QRadioButton("🌟 Resolusi Tinggi / High-DPI (1920 × 1080 - 300 DPI)")
        self.rb_res_high.setChecked(True)
        self.rb_res_high.setStyleSheet("font-weight: bold; color: #FFFFFF;")

        lbl_sub_high = QtWidgets.QLabel("    Kualitas prima sangat tajam saat disisipkan ke dokumen cetak.")
        lbl_sub_high.setStyleSheet("color: #8B949E; font-size: 11px;")

        self.rb_res_std = QtWidgets.QRadioButton("📱 Resolusi Layar Standar (Sesuai Ukuran Window)")
        self.rb_res_std.setStyleSheet("color: #C9D1D9;")

        v_res.addWidget(self.rb_res_high)
        v_res.addWidget(lbl_sub_high)
        v_res.addWidget(self.rb_res_std)
        layout.addWidget(grp_res)

        # Action Buttons
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_cancel = QtWidgets.QPushButton("Batal")
        self.btn_cancel.setStyleSheet("background-color: #21262D; color: #C9D1D9; border: 1px solid #30363D;")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_export = QtWidgets.QPushButton("💾 Pilih Lokasi & Simpan...")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #1F6FEB;
                color: #FFFFFF;
                border: 1px solid #388BFD;
            }
            QPushButton:hover {
                background-color: #388BFD;
            }
            QPushButton:pressed {
                background-color: #1158C7;
            }
        """)
        self.btn_export.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_export)
        layout.addLayout(btn_box)


class CSVImporterTab(QtWidgets.QWidget):
    """
    Tab for loading, inspecting, and plotting historical CSV mission data.
    Uses standard Python csv module and numpy.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = []
        self.rows_data = []  # List of dicts or list of lists
        self.column_data = {}  # col_name -> np.array of floats
        self.active_plotted_cols = []
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Top File Selection Bar
        file_bar = QtWidgets.QFrame()
        file_bar.setObjectName("hudCard")
        fb_layout = QtWidgets.QHBoxLayout(file_bar)
        fb_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_path = QtWidgets.QLabel("Pilih berkas CSV untuk dianalisis:")
        self.lbl_path.setStyleSheet("font-weight: 600; color: #c9d1d9;")

        self.txt_file_path = QtWidgets.QLineEdit()
        self.txt_file_path.setReadOnly(True)
        self.txt_file_path.setPlaceholderText("Belum ada file CSV yang dimuat...")

        self.btn_browse = QtWidgets.QPushButton("Browse CSV...")
        self.btn_browse.setObjectName("btnPrimary")
        self.btn_browse.clicked.connect(self.browse_csv)

        fb_layout.addWidget(self.lbl_path)
        fb_layout.addWidget(self.txt_file_path, stretch=1)
        fb_layout.addWidget(self.btn_browse)
        layout.addWidget(file_bar)

        # 2. Main Area Splitter (Left: Column Selector & Stats | Right: Interactive Plot & Table)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Left Panel (Controls & Summary)
        left_panel = QtWidgets.QWidget()
        lp_layout = QtWidgets.QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(6)

        # Columns Checklist with Checkboxes
        grp_cols = QtWidgets.QGroupBox("PILIH KOLOM UNTUK DI-PLOT (CHECKBOX)")
        gc_layout = QtWidgets.QVBoxLayout(grp_cols)

        self.list_columns = QtWidgets.QListWidget()
        self.list_columns.setStyleSheet("""
            QListWidget {
                background-color: #161616;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px 6px;
                color: #E0E0E0;
            }
            QListWidget::item:hover {
                background-color: #242424;
            }
            QListWidget::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.list_columns.itemChanged.connect(self.on_column_item_changed)
        gc_layout.addWidget(self.list_columns)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all_columns)
        self.btn_clear_sel = QtWidgets.QPushButton("Clear All")
        self.btn_clear_sel.clicked.connect(self.clear_column_selection)
        btn_row.addWidget(self.btn_select_all)
        btn_row.addWidget(self.btn_clear_sel)
        gc_layout.addLayout(btn_row)

        lp_layout.addWidget(grp_cols, stretch=2)

        # Statistics Summary Box
        grp_stats = QtWidgets.QGroupBox("STATISTIK DATA")
        gs_layout = QtWidgets.QVBoxLayout(grp_stats)
        self.txt_stats = QtWidgets.QTextBrowser()
        self.txt_stats.setPlaceholderText("Statistik ringkas akan muncul setelah file CSV dimuat...")
        gs_layout.addWidget(self.txt_stats)
        lp_layout.addWidget(grp_stats, stretch=1)

        splitter.addWidget(left_panel)

        # Right Panel (Plot + Table in Tabs)
        right_panel = QtWidgets.QTabWidget()

        # Sub-tab 1: Graph Plot
        plot_tab = QtWidgets.QWidget()
        pt_layout = QtWidgets.QVBoxLayout(plot_tab)
        pt_layout.setContentsMargins(6, 6, 6, 6)
        pt_layout.setSpacing(6)

        # Graph Toolbar (Auto Fit, Normalization, & Nominal Info HUD)
        self.toolbar_frame = QtWidgets.QFrame()
        self.toolbar_frame.setStyleSheet("background-color: #181818; border: 1px solid #333333; border-radius: 4px; padding: 2px 6px;")
        tb_layout = QtWidgets.QHBoxLayout(self.toolbar_frame)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(10)

        self.btn_autoscale = QtWidgets.QPushButton("⟳ Auto Fit Scale")
        self.btn_autoscale.setStyleSheet("background-color: #D32F2F; color: #FFFFFF; font-weight: bold; padding: 4px 10px; border-radius: 3px;")
        self.btn_autoscale.setToolTip("Skala ulang grafik otomatis agar pas dengan nilai minimum dan maksimum data yang dipilih")
        self.btn_autoscale.clicked.connect(self.auto_fit_view)
        tb_layout.addWidget(self.btn_autoscale)

        self.cb_normalize = QtWidgets.QCheckBox("Normalisasi (0 - 100%)")
        self.cb_normalize.setStyleSheet("font-weight: bold; color: #CCCCCC; font-size: 11px;")
        self.cb_normalize.setToolTip("Gunakan mode normalisasi untuk membandingkan bentuk kurva beberapa parameter berbeda satuan (misal pH ~7 vs PWM ~1500)")
        self.cb_normalize.toggled.connect(self.update_plot)
        tb_layout.addWidget(self.cb_normalize)

        self.btn_export_image = QtWidgets.QPushButton("📥 Unduh Grafik...")
        self.btn_export_image.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: #FFFFFF;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 3px;
                border: 1px solid #2196F3;
            }
            QPushButton:hover {
                background-color: #2196F3;
                border-color: #64B5F6;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.btn_export_image.setToolTip("Unduh dan simpan gambar grafik untuk keperluan laporan, dokumen Word, skripsi, atau paper ilmiah.")
        self.btn_export_image.clicked.connect(self.export_graph_image)
        tb_layout.addWidget(self.btn_export_image)

        tb_layout.addStretch()

        # Live Nominal Value Hover Badge
        self.lbl_hover_info = QtWidgets.QLabel("Arahkan kursor ke grafik untuk membaca nilai nominal titik...")
        self.lbl_hover_info.setStyleSheet("color: #4A90D9; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;")
        tb_layout.addWidget(self.lbl_hover_info)

        pt_layout.addWidget(self.toolbar_frame)

        # Main Plot Widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#141414")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.35)
        self.plot_widget.addLegend(offset=(12, 12))
        self.plot_widget.setLabel('bottom', "Index Sampel / Titik Waktu")
        self.plot_widget.setLabel('left', "Nilai Terukur / Nominal")

        # Crosshair Lines
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FF5252', width=1, style=QtCore.Qt.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#FF5252', width=1, style=QtCore.Qt.DashLine))
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)

        # Mouse Hover Signal Proxy
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.on_mouse_moved)

        pt_layout.addWidget(self.plot_widget)
        right_panel.addTab(plot_tab, "Grafik Analisis")

        # Sub-tab 2: Data Table Preview
        table_tab = QtWidgets.QWidget()
        tt_layout = QtWidgets.QVBoxLayout(table_tab)
        tt_layout.setContentsMargins(4, 4, 4, 4)

        self.data_table = QtWidgets.QTableWidget()
        tt_layout.addWidget(self.data_table)
        right_panel.addTab(table_tab, "Tabel Preview Data")

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter, stretch=1)

        # Diverse Vibrant Color Palette
        self.colors = [
            '#FF5252', '#448AFF', '#69F0AE', '#FFD740', '#E040FB', '#18FFFF', '#FF6E40', '#B388FF'
        ]

    def browse_csv(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Buka Berkas CSV Telemetri", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.load_csv(file_path)

    def load_csv(self, file_path: str):
        self.txt_file_path.setText(file_path)
        try:
            raw_rows = []
            with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if not headers:
                    QtWidgets.QMessageBox.warning(self, "CSV Kosong", "File CSV tidak memiliki data atau header.")
                    return
                for r in reader:
                    if r:
                        raw_rows.append(r)

            self.headers = [h.strip() for h in headers]
            self.rows_data = raw_rows

            # Parse numeric columns
            self.column_data = {}
            for col_idx, col_name in enumerate(self.headers):
                vals = []
                for row in self.rows_data:
                    if col_idx < len(row):
                        try:
                            vals.append(float(row[col_idx]))
                        except (ValueError, TypeError):
                            pass
                if len(vals) > 0 and len(vals) >= len(self.rows_data) * 0.5:
                    self.column_data[col_name] = np.array(vals, dtype=float)

            # Populate Column Selector with Checkboxes
            self.list_columns.blockSignals(True)
            self.list_columns.clear()

            default_checked = ["PH", "DO_MGL", "DEPTH_M"]
            has_checked = False
            for col_name in self.column_data.keys():
                item = QtWidgets.QListWidgetItem(col_name)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                # Check default primary parameters or first available
                if col_name in default_checked and not has_checked:
                    item.setCheckState(QtCore.Qt.Checked)
                    has_checked = True
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
                self.list_columns.addItem(item)

            # Fallback if none matched default
            if not has_checked and self.list_columns.count() > 0:
                self.list_columns.item(0).setCheckState(QtCore.Qt.Checked)

            self.list_columns.blockSignals(False)

            # Populate Table Preview (first 100 rows)
            self.populate_table(self.headers, self.rows_data[:100])

            # Calculate Statistics
            self.calculate_statistics()

            # Plot with Auto Scale
            self.update_plot()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal Memuat CSV", f"Error saat membaca file CSV:\n{e}")

    def populate_table(self, headers, rows):
        self.data_table.clear()
        self.data_table.setRowCount(len(rows))
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)

        for row_idx, row in enumerate(rows):
            for col_idx, val in enumerate(row):
                if col_idx < len(headers):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    self.data_table.setItem(row_idx, col_idx, item)

    def calculate_statistics(self):
        total_rows = len(self.rows_data)
        stats_text = f"<b>Total Sampel:</b> {total_rows} baris<br>"
        stats_text += f"<b>Total Parameter:</b> {len(self.headers)} kolom<br><hr>"

        for col_name, arr in self.column_data.items():
            if len(arr) > 0:
                c_min = float(np.min(arr))
                c_max = float(np.max(arr))
                c_mean = float(np.mean(arr))
                c_std = float(np.std(arr))
                stats_text += (
                    f"<b>{col_name}</b>:<br>"
                    f"  Min: {c_min:.2f} | Max: {c_max:.2f}<br>"
                    f"  Rata-rata: {c_mean:.2f} ± {c_std:.2f}<br><br>"
                )
        self.txt_stats.setHtml(stats_text)

    def on_column_item_changed(self, item):
        self.update_plot()

    def select_all_columns(self):
        self.list_columns.blockSignals(True)
        for i in range(self.list_columns.count()):
            self.list_columns.item(i).setCheckState(QtCore.Qt.Checked)
        self.list_columns.blockSignals(False)
        self.update_plot()

    def clear_column_selection(self):
        self.list_columns.blockSignals(True)
        for i in range(self.list_columns.count()):
            self.list_columns.item(i).setCheckState(QtCore.Qt.Unchecked)
        self.list_columns.blockSignals(False)
        self.update_plot()

    def update_plot(self):
        # 1. Clear previous curves
        for item in list(self.plot_widget.listDataItems()):
            self.plot_widget.removeItem(item)

        # 2. Gather checked columns
        checked_cols = []
        for i in range(self.list_columns.count()):
            item = self.list_columns.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                checked_cols.append(item.text())

        self.active_plotted_cols = checked_cols
        if not checked_cols:
            self.lbl_hover_info.setText("Centang minimal satu kolom di panel kiri untuk menampilkan grafik.")
            return

        is_normalized = self.cb_normalize.isChecked()
        all_plotted_data = []
        stats_summary_parts = []

        for idx, col_name in enumerate(checked_cols):
            if col_name in self.column_data:
                raw_y = self.column_data[col_name]
                color = self.colors[idx % len(self.colors)]

                c_min = float(np.nanmin(raw_y))
                c_max = float(np.nanmax(raw_y))
                c_mean = float(np.nanmean(raw_y))
                stats_summary_parts.append(f"<span style='color:{color}'>{col_name}</span>: [{c_min:.2f} s/d {c_max:.2f}, μ={c_mean:.2f}]")

                if is_normalized:
                    if abs(c_max - c_min) > 1e-6:
                        y_plot = (raw_y - c_min) / (c_max - c_min) * 100.0
                    else:
                        y_plot = np.full_like(raw_y, 50.0)
                    curve_name = f"{col_name} (0-100%)"
                else:
                    y_plot = raw_y
                    curve_name = col_name

                all_plotted_data.append(y_plot)
                self.plot_widget.plot(
                    y_plot,
                    pen=pg.mkPen(color, width=2.2),
                    name=curve_name
                )

        # Update initial nominal summary in toolbar
        self.lbl_hover_info.setText(" | ".join(stats_summary_parts[:2]) + ("..." if len(stats_summary_parts) > 2 else ""))

        # 3. Dynamic Auto-Scaling (fits precisely to actual min & max)
        self.auto_fit_view(all_plotted_data, is_normalized)

    def auto_fit_view(self, data_list=None, is_normalized=None):
        if not self.active_plotted_cols:
            return

        if is_normalized is None:
            is_normalized = self.cb_normalize.isChecked()

        if is_normalized:
            self.plot_widget.setYRange(-5.0, 105.0, padding=0.03)
            self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
            return

        if data_list is None:
            data_list = [self.column_data[c] for c in self.active_plotted_cols if c in self.column_data]

        if data_list:
            min_val = min(float(np.nanmin(d)) for d in data_list)
            max_val = max(float(np.nanmax(d)) for d in data_list)
            span = max_val - min_val

            # If range is very small or zero (e.g. steady pH 7.37), expand around it
            if span < 1e-4:
                pad = 0.5 if abs(max_val) < 1.0 else abs(max_val) * 0.05
                self.plot_widget.setYRange(min_val - pad, max_val + pad, padding=0.05)
            else:
                # Tight auto-range padding so fluctuations are prominent and readable
                padding_y = span * 0.08
                self.plot_widget.setYRange(min_val - padding_y, max_val + padding_y, padding=0.02)

            max_len = max(len(d) for d in data_list)
            self.plot_widget.setXRange(0, max(1, max_len - 1), padding=0.02)

    def on_mouse_moved(self, evt):
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
            x_idx = int(round(mouse_point.x()))
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())

            if self.active_plotted_cols:
                readout_parts = [f"Titik #{x_idx}"]
                for col_name in self.active_plotted_cols:
                    arr = self.column_data.get(col_name)
                    if arr is not None and 0 <= x_idx < len(arr):
                        val = arr[x_idx]
                        readout_parts.append(f"{col_name}: <b>{val:.2f}</b>")
                if len(readout_parts) > 1:
                    self.lbl_hover_info.setText(" | ".join(readout_parts))

    def export_graph_image(self):
        """
        Exports the current plot to a publication-ready image file (PNG/JPG).
        Supports Document Mode (White Background) and High-DPI for thesis/reports.
        """
        if not self.active_plotted_cols:
            QtWidgets.QMessageBox.warning(
                self, "Tidak Ada Data",
                "Silakan muat berkas CSV dan centang minimal satu kolom data di panel kiri sebelum mengunduh gambar grafik."
            )
            return

        dlg = ExportGraphDialog(self, active_cols=self.active_plotted_cols)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        is_white = dlg.rb_white.isChecked()
        is_high_dpi = dlg.rb_res_high.isChecked()

        cols_tag = "_".join(self.active_plotted_cols[:3])
        theme_tag = "doc_white" if is_white else "gui_dark"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"grafik_{cols_tag}_{theme_tag}_{timestamp}.png"

        curr_dir = os.path.dirname(self.txt_file_path.text()) if self.txt_file_path.text() else "./data_logs"
        initial_path = os.path.join(curr_dir, default_filename)

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Simpan Gambar Grafik untuk Dokumen",
            initial_path,
            "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)"
        )
        if not file_path:
            return

        if not (file_path.lower().endswith(".png") or file_path.lower().endswith(".jpg") or file_path.lower().endswith(".jpeg")):
            file_path += ".png"

        # Hide crosshair lines during export
        self.v_line.setVisible(False)
        self.h_line.setVisible(False)

        bottom_axis = self.plot_widget.getAxis('bottom')
        left_axis = self.plot_widget.getAxis('left')
        legend = self.plot_widget.plotItem.legend

        orig_bg = self.plot_widget.backgroundBrush()
        orig_bottom_pen = bottom_axis.pen()
        orig_bottom_textPen = bottom_axis.textPen()
        orig_left_pen = left_axis.pen()
        orig_left_textPen = left_axis.textPen()

        try:
            if is_white:
                self.plot_widget.setBackground('#FFFFFF')
                bottom_axis.setPen(pg.mkPen('#222222', width=1.5))
                bottom_axis.setTextPen(pg.mkPen('#222222'))
                left_axis.setPen(pg.mkPen('#222222', width=1.5))
                left_axis.setTextPen(pg.mkPen('#222222'))
                if legend:
                    legend.setBrush(pg.mkBrush(255, 255, 255, 220))
                    legend.setPen(pg.mkPen('#CCCCCC', width=1))
                    for sample, label in legend.items:
                        label.setText(label.text, color='#222222')

            QtWidgets.QApplication.processEvents()

            exporter = pge.ImageExporter(self.plot_widget.plotItem)
            if is_high_dpi:
                exporter.parameters()['width'] = 1920

            exporter.export(file_path)

            theme_name = "Format Dokumen (Latar Putih)" if is_white else "Format GUI (Latar Gelap)"
            res_name = "High-DPI 1920px (300 DPI)" if is_high_dpi else "Ukuran Layar Standar"
            QtWidgets.QMessageBox.information(
                self, "Unduh Grafik Berhasil",
                f"Gambar grafik berhasil disimpan!\n\n"
                f"Lokasi Berkas:\n{file_path}\n\n"
                f"Format Tampilan: {theme_name}\n"
                f"Kualitas Resolusi: {res_name}\n\n"
                f"Gambar siap disisipkan ke dokumen skripsi, jurnal, atau laporan Word/PDF Anda!"
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Gagal Menyimpan Gambar",
                f"Terjadi kesalahan saat mengekspor gambar grafik:\n{e}"
            )
        finally:
            if is_white:
                self.plot_widget.setBackground(orig_bg)
                bottom_axis.setPen(orig_bottom_pen)
                bottom_axis.setTextPen(orig_bottom_textPen)
                left_axis.setPen(orig_left_pen)
                left_axis.setTextPen(orig_left_textPen)
                if legend:
                    legend.setBrush(pg.mkBrush(20, 20, 20, 200))
                    legend.setPen(pg.mkPen('#444444', width=1))
                    for sample, label in legend.items:
                        label.setText(label.text, color='#E0E0E0')
            self.v_line.setVisible(True)
            self.h_line.setVisible(True)
            QtWidgets.QApplication.processEvents()

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name
        if hasattr(self, "toolbar_frame"):
            if is_dark:
                self.toolbar_frame.setStyleSheet("background-color: #181818; border: 1px solid #333333; border-radius: 4px; padding: 2px 6px;")
                self.cb_normalize.setStyleSheet("font-weight: bold; color: #CCCCCC; font-size: 11px;")
            else:
                self.toolbar_frame.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 6px;")
                self.cb_normalize.setStyleSheet("font-weight: bold; color: #0F172A; font-size: 11px;")

        if hasattr(self, "list_columns"):
            if is_dark:
                self.list_columns.setStyleSheet("""
                    QListWidget {
                        background-color: #161616;
                        border: 1px solid #333333;
                        border-radius: 4px;
                    }
                    QListWidget::item {
                        padding: 4px 6px;
                        color: #E0E0E0;
                    }
                    QListWidget::item:hover {
                        background-color: #242424;
                    }
                """)
            else:
                self.list_columns.setStyleSheet("""
                    QListWidget {
                        background-color: #ffffff;
                        border: 1px solid #cbd5e1;
                        border-radius: 4px;
                    }
                    QListWidget::item {
                        padding: 4px 6px;
                        color: #0F172A;
                    }
                    QListWidget::item:hover {
                        background-color: #f1f5f9;
                    }
                """)

        if hasattr(self, "plot_widget"):
            bg_clr = "#141414" if is_dark else "#FFFFFF"
            self.plot_widget.setBackground(bg_clr)
            pen_clr = "#9AA0A6" if is_dark else "#334155"
            axis_pen = pg.mkPen(color=pen_clr, width=1)
            self.plot_widget.getAxis('bottom').setPen(axis_pen)
            self.plot_widget.getAxis('left').setPen(axis_pen)
            self.plot_widget.getAxis('bottom').setTextPen(axis_pen)
            self.plot_widget.getAxis('left').setTextPen(axis_pen)


