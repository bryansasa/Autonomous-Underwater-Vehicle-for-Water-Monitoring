# -*- coding: utf-8 -*-
"""
Thruster Matrix & LMPC Motion Monitor Widget for Submersible GCS
Displays 6 Thruster PWM power bars and 4 DoF Decoupled LMPC Force Allocation.
"""
from typing import Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui


class BiDirectionalBar(QtWidgets.QWidget):
    """
    Sleek, custom-rendered bidirectional PWM gauge.
    Center is 1500 µs (neutral / 0 thrust).
    Forward thrust (>1500 µs) expands smoothly to the right (Sky Blue / Cyan).
    Reverse thrust (<1500 µs) expands smoothly to the left (Warm Amber).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pwm = 1500
        self.is_dark = True
        self.setFixedHeight(8)
        self.setMinimumWidth(80)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.update()

    def set_pwm(self, pwm: int):
        self.pwm = max(1100, min(1900, pwm))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Background track
        bg_rect = QtCore.QRectF(0, 0, w, h)
        if self.is_dark:
            painter.setPen(QtGui.QPen(QtGui.QColor("#242c3d"), 1.0))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#11141c")))
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor("#cbd5e1"), 1.0))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#f1f5f9")))
        painter.drawRoundedRect(bg_rect, radius, radius)

        # Center position
        cx = w / 2.0
        delta = self.pwm - 1500
        max_delta = 400.0  # 1100 to 1900 us range

        # Active thrust bar (expanding from center)
        if abs(delta) >= 8:
            pct = delta / max_delta
            bar_w = abs(pct) * (w / 2.0 - 2.0)
            if delta > 0:
                bar_rect = QtCore.QRectF(cx, 1.5, bar_w, h - 3.0)
                color = QtGui.QColor("#0ea5e9")  # Cyan / Sky Blue
            else:
                bar_rect = QtCore.QRectF(cx - bar_w, 1.5, bar_w, h - 3.0)
                color = QtGui.QColor("#f59e0b")  # Warm Amber

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRoundedRect(bar_rect, 2.0, 2.0)

        # Center neutral tick
        tick_clr = QtGui.QColor("#64748b") if self.is_dark else QtGui.QColor("#94a3b8")
        painter.setPen(QtGui.QPen(tick_clr, 1.5))
        painter.drawLine(QtCore.QPointF(cx, 1.0), QtCore.QPointF(cx, h - 1.0))


class SingleThrusterBar(QtWidgets.QFrame):
    """
    Renders an individual thruster PWM gauge with neutral 1500 µs center.
    """
    def __init__(self, name: str, orientation: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.orientation = orientation
        self.pwm = 1500

        self.setStyleSheet("""
            SingleThrusterBar {
                background-color: #141720;
                border: 1px solid #222938;
                border-radius: 4px;
                padding: 2px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        # Header Row
        hdr = QtWidgets.QHBoxLayout()
        self.lbl_name = QtWidgets.QLabel(name)
        self.lbl_name.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")

        self.lbl_pwm = QtWidgets.QLabel("1500 µs")
        self.lbl_pwm.setStyleSheet("color: #e2e8f0; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")

        hdr.addWidget(self.lbl_name)
        hdr.addStretch()
        hdr.addWidget(self.lbl_pwm)
        layout.addLayout(hdr)

        # Custom Bi-directional Progress Bar
        self.gauge = BiDirectionalBar(self)
        layout.addWidget(self.gauge)

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name
        self.gauge.set_theme(is_dark)
        if is_dark:
            self.setStyleSheet("""
                SingleThrusterBar {
                    background-color: #141720;
                    border: 1px solid #222938;
                    border-radius: 4px;
                    padding: 2px;
                }
            """)
            self.lbl_name.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
        else:
            self.setStyleSheet("""
                SingleThrusterBar {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    padding: 2px;
                }
            """)
            self.lbl_name.setStyleSheet("color: #475569; font-size: 10px; font-weight: 600;")
        self.set_pwm(self.pwm)

    def set_pwm(self, pwm: int):
        self.pwm = max(1100, min(1900, pwm))
        self.gauge.set_pwm(self.pwm)

        delta = self.pwm - 1500
        if abs(delta) < 10:
            self.lbl_pwm.setText(f"{self.pwm} µs")
            self.lbl_pwm.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        elif delta > 0:
            self.lbl_pwm.setText(f"{self.pwm} µs")
            self.lbl_pwm.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        else:
            self.lbl_pwm.setText(f"{self.pwm} µs")
            self.lbl_pwm.setStyleSheet("color: #fbbf24; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")


class MicroForceBar(QtWidgets.QWidget):
    """Micro bidirectional gauge for force magnitude visualization."""
    def __init__(self, max_val=20.0, parent=None):
        super().__init__(parent)
        self.val = 0.0
        self.max_val = max_val
        self.is_dark = True
        self.setFixedHeight(4)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.update()

    def set_val(self, val: float):
        self.val = max(-self.max_val, min(self.max_val, val))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Background track
        painter.setPen(QtCore.Qt.NoPen)
        track_clr = QtGui.QColor("#1b202c") if self.is_dark else QtGui.QColor("#e2e8f0")
        painter.setBrush(QtGui.QBrush(track_clr))
        painter.drawRoundedRect(QtCore.QRectF(0, 0, w, h), radius, radius)

        # Center line & active bar
        cx = w / 2.0
        if abs(self.val) > 0.05:
            pct = self.val / self.max_val
            bar_w = abs(pct) * (cx - 1.0)
            color = QtGui.QColor("#38bdf8") if self.val >= 0 else QtGui.QColor("#f59e0b")
            bar_x = cx if self.val >= 0 else (cx - bar_w)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRoundedRect(QtCore.QRectF(bar_x, 0.5, bar_w, h - 1.0), 1.0, 1.0)

        # Center tick
        tick_clr = QtGui.QColor("#475569") if self.is_dark else QtGui.QColor("#94a3b8")
        painter.setPen(QtGui.QPen(tick_clr, 1.0))
        painter.drawLine(QtCore.QPointF(cx, 0), QtCore.QPointF(cx, h))


class ThrusterMatrix(QtWidgets.QGroupBox):
    """
    6-Thruster Propulsion & Force Allocation Monitor.
    Features:
      - 6 Thruster bi-directional PWM gauges (Horizontal 45° Vectored + Vertical Heave)
      - 4-DoF Virtual Control Force Cards (Surge, Sway, Heave, Yaw)
      - Real-Time Solver & Thruster Allocation Diagnostics
    """
    def __init__(self, parent=None):
        super().__init__("STATUS PENDORONG & GAYA KONTROL", parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setMinimumWidth(260)
        self.force_cards_list = []
        self.init_ui()

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(260, 175)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(320, 205)

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 6)
        main_layout.setSpacing(6)

        # 1. 6 Thruster Bars Grid
        t_grid = QtWidgets.QGridLayout()
        t_grid.setSpacing(5)

        # 4 Horizontal (Vectored 45°)
        self.t1 = SingleThrusterBar("T1 Depan Kiri (45°)", "horizontal")
        self.t2 = SingleThrusterBar("T2 Depan Kanan (45°)", "horizontal")
        self.t3 = SingleThrusterBar("T3 Belakang Kiri (45°)", "horizontal")
        self.t4 = SingleThrusterBar("T4 Belakang Kanan (45°)", "horizontal")

        # 2 Vertical
        self.t5 = SingleThrusterBar("T5 Vertikal Kiri", "vertical")
        self.t6 = SingleThrusterBar("T6 Vertikal Kanan", "vertical")

        t_grid.addWidget(self.t1, 0, 0)
        t_grid.addWidget(self.t2, 0, 1)
        t_grid.addWidget(self.t3, 1, 0)
        t_grid.addWidget(self.t4, 1, 1)
        t_grid.addWidget(self.t5, 2, 0)
        t_grid.addWidget(self.t6, 2, 1)
        main_layout.addLayout(t_grid)

        # 2. 4-DoF Virtual Forces Container
        self.forces_container = QtWidgets.QFrame()
        self.forces_container.setStyleSheet("""
            QFrame {
                background-color: #12151e;
                border: 1px solid #202636;
                border-radius: 5px;
            }
        """)
        fc_layout = QtWidgets.QVBoxLayout(self.forces_container)
        fc_layout.setContentsMargins(8, 6, 8, 6)
        fc_layout.setSpacing(5)

        fc_hdr = QtWidgets.QHBoxLayout()
        self.lbl_fc_title = QtWidgets.QLabel("GAYA KONTROL VIRTUAL (4-DOF)")
        self.lbl_fc_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        
        self.lbl_alloc_mode = QtWidgets.QLabel("Alokasi: QP")
        self.lbl_alloc_mode.setStyleSheet("""
            color: #38bdf8;
            font-size: 9px;
            font-weight: 600;
            background-color: #0c4a6e;
            border: 1px solid #0369a1;
            border-radius: 3px;
            padding: 1px 6px;
        """)
        fc_hdr.addWidget(self.lbl_fc_title)
        fc_hdr.addStretch()
        fc_hdr.addWidget(self.lbl_alloc_mode)
        fc_layout.addLayout(fc_hdr)

        # 4 Clean Engineering Cards (No tacky rainbow borders)
        forces_row = QtWidgets.QHBoxLayout()
        forces_row.setSpacing(5)

        # Surge
        card_surge, self.lbl_f_surge, self.bar_f_surge = self._create_force_card("SURGE (τx)", "Maju / Mundur", "+0.00 N", 20.0)
        forces_row.addWidget(card_surge)

        # Sway
        card_sway, self.lbl_f_sway, self.bar_f_sway = self._create_force_card("SWAY (τy)", "Geser Lateral", "+0.00 N", 20.0)
        forces_row.addWidget(card_sway)

        # Heave
        card_heave, self.lbl_f_heave, self.bar_f_heave = self._create_force_card("HEAVE (τz)", "Kedalaman", "+0.00 N", 25.0)
        forces_row.addWidget(card_heave)

        # Yaw
        card_yaw, self.lbl_t_yaw, self.bar_t_yaw = self._create_force_card("YAW (τψ)", "Rotasi Haluan", "+0.00 Nm", 10.0)
        forces_row.addWidget(card_yaw)

        fc_layout.addLayout(forces_row)

        # Diagnostics Bottom Sub-bar
        diag_row = QtWidgets.QHBoxLayout()
        diag_row.setContentsMargins(2, 2, 2, 0)
        diag_row.setSpacing(10)

        # Total Thrust
        self.lbl_tot_thrust = QtWidgets.QLabel("Total Gaya: 0.0 N")
        self.lbl_tot_thrust.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
        diag_row.addWidget(self.lbl_tot_thrust)

        # Saturation Margin
        self.lbl_headroom = QtWidgets.QLabel("Margin: 100% (Aman)")
        self.lbl_headroom.setMinimumWidth(125)
        self.lbl_headroom.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 600;")
        diag_row.addWidget(self.lbl_headroom)

        diag_row.addStretch()

        # Solver Latency Gauge
        self.lbl_wcet_title = QtWidgets.QLabel("Komputasi:")
        self.lbl_wcet_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
        diag_row.addWidget(self.lbl_wcet_title)

        self.wcet_bar = QtWidgets.QProgressBar()
        self.wcet_bar.setRange(0, 100)
        self.wcet_bar.setValue(12)
        self.wcet_bar.setFixedSize(45, 6)
        self.wcet_bar.setTextVisible(False)
        self.wcet_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 2px;
            }
        """)
        diag_row.addWidget(self.wcet_bar)

        self.lbl_wcet = QtWidgets.QLabel("12.0 ms")
        self.lbl_wcet.setStyleSheet("color: #e2e8f0; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        diag_row.addWidget(self.lbl_wcet)

        fc_layout.addLayout(diag_row)
        main_layout.addWidget(self.forces_container)

    def _create_force_card(self, title: str, subtitle: str, init_val: str, max_val: float):
        f = QtWidgets.QFrame()
        f.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        f.setMinimumWidth(55)
        f.setStyleSheet("""
            QFrame {
                background-color: #171b26;
                border: 1px solid #252c3c;
                border-radius: 4px;
                padding: 1px;
            }
        """)
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(6, 4, 6, 4)
        l.setSpacing(2)

        lbl_t = QtWidgets.QLabel(title)
        lbl_t.setStyleSheet("color: #cbd5e1; font-size: 9px; font-weight: 700; letter-spacing: 0.3px;")
        l.addWidget(lbl_t)

        lbl_sub = QtWidgets.QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #64748b; font-size: 8px;")
        l.addWidget(lbl_sub)

        lbl_v = QtWidgets.QLabel(init_val)
        lbl_v.setObjectName("val")
        lbl_v.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        l.addWidget(lbl_v)

        bar = MicroForceBar(max_val, f)
        l.addWidget(bar)

        if not hasattr(self, "force_cards_list"):
            self.force_cards_list = []
        self.force_cards_list.append((f, lbl_t, lbl_sub, lbl_v, bar))

        return f, lbl_v, bar

    def apply_theme(self, theme_name: str):
        is_dark = "Dark" in theme_name
        for t in [self.t1, self.t2, self.t3, self.t4, self.t5, self.t6]:
            t.apply_theme(theme_name)

        if hasattr(self, "forces_container"):
            if is_dark:
                self.forces_container.setStyleSheet("""
                    QFrame {
                        background-color: #12151e;
                        border: 1px solid #202636;
                        border-radius: 5px;
                    }
                """)
                self.lbl_fc_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
                self.lbl_tot_thrust.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600;")
                self.lbl_wcet_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
                self.lbl_wcet.setStyleSheet("color: #e2e8f0; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
            else:
                self.forces_container.setStyleSheet("""
                    QFrame {
                        background-color: #f8fafc;
                        border: 1px solid #cbd5e1;
                        border-radius: 5px;
                    }
                """)
                self.lbl_fc_title.setStyleSheet("color: #334155; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
                self.lbl_tot_thrust.setStyleSheet("color: #334155; font-size: 10px; font-weight: 600;")
                self.lbl_wcet_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 600;")
                self.lbl_wcet.setStyleSheet("color: #0f172a; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")

        if hasattr(self, "force_cards_list"):
            for f, lbl_t, lbl_sub, lbl_v, bar in self.force_cards_list:
                bar.set_theme(is_dark)
                if is_dark:
                    f.setStyleSheet("""
                        QFrame {
                            background-color: #171b26;
                            border: 1px solid #252c3c;
                            border-radius: 4px;
                            padding: 1px;
                        }
                    """)
                    lbl_t.setStyleSheet("color: #cbd5e1; font-size: 9px; font-weight: 700; letter-spacing: 0.3px;")
                    lbl_sub.setStyleSheet("color: #64748b; font-size: 8px;")
                    lbl_v.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
                else:
                    f.setStyleSheet("""
                        QFrame {
                            background-color: #ffffff;
                            border: 1px solid #cbd5e1;
                            border-radius: 4px;
                            padding: 1px;
                        }
                    """)
                    lbl_t.setStyleSheet("color: #334155; font-size: 9px; font-weight: 700; letter-spacing: 0.3px;")
                    lbl_sub.setStyleSheet("color: #64748b; font-size: 8px;")
                    lbl_v.setStyleSheet("color: #0f172a; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")

    def update_telemetry(self, data: Dict[str, Any]):
        # Update 6 PWMs
        pwms = [
            data.get("pwm1", 1500),
            data.get("pwm2", 1500),
            data.get("pwm3", 1500),
            data.get("pwm4", 1500),
            data.get("pwm5", data.get("pwm_main", 1500)),
            data.get("pwm6", data.get("pwm_main", 1500))
        ]
        self.t1.set_pwm(pwms[0])
        self.t2.set_pwm(pwms[1])
        self.t3.set_pwm(pwms[2])
        self.t4.set_pwm(pwms[3])
        self.t5.set_pwm(pwms[4])
        self.t6.set_pwm(pwms[5])

        # Update 4 DoF Virtual Forces
        f_surge = data.get("virtual_force_surge", 0.0)
        f_sway = data.get("virtual_force_sway", 0.0)
        f_heave = data.get("virtual_force_heave", data.get("pid_output", 0.0))
        t_yaw = data.get("virtual_torque_yaw", 0.0)
        wcet = data.get("lmpc_wcet", data.get("lmpc_wcet_ms", 12.0))

        self.lbl_f_surge.setText(f"{f_surge:+.2f} N")
        self.bar_f_surge.set_val(f_surge)

        self.lbl_f_sway.setText(f"{f_sway:+.2f} N")
        self.bar_f_sway.set_val(f_sway)

        self.lbl_f_heave.setText(f"{f_heave:+.2f} N")
        self.bar_f_heave.set_val(f_heave)

        self.lbl_t_yaw.setText(f"{t_yaw:+.2f} Nm")
        self.bar_t_yaw.set_val(t_yaw)

        # Total combined thrust estimate (approx 0.025 N per delta us)
        tot_thrust = sum(abs(p - 1500) for p in pwms) * 0.025
        self.lbl_tot_thrust.setText(f"Total Gaya: {tot_thrust:.1f} N")

        # Saturation margin (highest thruster delta / 400us max)
        max_delta = max(abs(p - 1500) for p in pwms)
        headroom_pct = max(0, int((1.0 - (max_delta / 400.0)) * 100))
        if headroom_pct < 15:
            self.lbl_headroom.setText(f"Headroom: {headroom_pct}% (SATURASI!)")
            self.lbl_headroom.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: 700;")
        elif headroom_pct < 35:
            self.lbl_headroom.setText(f"Headroom: {headroom_pct}% (Tinggi)")
            self.lbl_headroom.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: 600;")
        else:
            self.lbl_headroom.setText(f"Headroom: {headroom_pct}% (Aman)")
            self.lbl_headroom.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 600;")

        # WCET Execution
        self.wcet_bar.setValue(int(min(100, wcet)))
        if wcet <= 50.0:
            self.lbl_wcet.setText(f"{wcet:.1f} ms (OK)")
            self.lbl_wcet.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
            self.wcet_bar.setStyleSheet("""
                QProgressBar { background-color: #1a202c; border: 1px solid #2d3748; border-radius: 3px; }
                QProgressBar::chunk { background-color: #38bdf8; border-radius: 2px; }
            """)
        elif wcet <= 100.0:
            self.lbl_wcet.setText(f"{wcet:.1f} ms (PERINGATAN)")
            self.lbl_wcet.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
            self.wcet_bar.setStyleSheet("""
                QProgressBar { background-color: #1a202c; border: 1px solid #2d3748; border-radius: 3px; }
                QProgressBar::chunk { background-color: #f59e0b; border-radius: 2px; }
            """)
        else:
            self.lbl_wcet.setText(f"{wcet:.1f} ms (OVERLOAD)")
            self.lbl_wcet.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
            self.wcet_bar.setStyleSheet("""
                QProgressBar { background-color: #1a202c; border: 1px solid #2d3748; border-radius: 3px; }
                QProgressBar::chunk { background-color: #ef4444; border-radius: 2px; }
            """)
