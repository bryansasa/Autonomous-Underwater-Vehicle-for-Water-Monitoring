# -*- coding: utf-8 -*-
"""
Primary Flight Display (PFD) Widget for Submersible GCS
Renders Artificial Horizon (Pitch/Roll), Heading Compass Tape (Yaw), and Depth Ladder Tape.
"""
import math
from PyQt5 import QtWidgets, QtCore, QtGui


class PFDWidget(QtWidgets.QWidget):
    """
    Tactical Flight HUD inspired by QGroundControl Primary Flight Display.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # State Variables
        self.roll = 0.0          # degrees (-180 to 180)
        self.pitch = 0.0        # degrees (-90 to 90)
        self.yaw = 0.0          # degrees (0 to 360)
        self.target_yaw = 0.0

        self.depth = 0.0        # meters (0.0 to 5.0+)
        self.target_depth = 0.0 # meters
        self.vertical_speed = 0.0 # m/s

        # EKF Estimated Current Disturbance (Surge, Sway)
        self.disturb_surge = 0.0
        self.disturb_sway = 0.0

        # Colors
        self.sky_color = QtGui.QColor(15, 76, 129)     # Deep navy / water top
        self.ground_color = QtGui.QColor(26, 42, 58)  # Deep underwater
        self.horizon_line = QtGui.QColor(229, 57, 53) # Tactical red accent
        self.pitch_ladder_color = QtGui.QColor(240, 246, 252)
        self.tape_bg = QtGui.QColor(26, 29, 35, 200)

    def update_attitude(self, roll: float, pitch: float, yaw: float, depth: float,
                        target_depth: float = 0.0, target_yaw: float = 0.0,
                        disturb_surge: float = 0.0, disturb_sway: float = 0.0):
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw % 360.0
        self.depth = depth
        self.target_depth = target_depth
        self.target_yaw = target_yaw % 360.0
        self.disturb_surge = disturb_surge
        self.disturb_sway = disturb_sway
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        # 1. Background Fill
        painter.fillRect(0, 0, w, h, QtGui.QColor(26, 29, 35))

        # 2. Draw Artificial Horizon (Rotated by Roll and Translated by Pitch)
        self.draw_horizon(painter, cx, cy, w, h)

        # 3. Draw Pitch Ladder & Center Reticle
        self.draw_pitch_ladder(painter, cx, cy, w, h)
        self.draw_aircraft_reticle(painter, cx, cy)

        # 4. Draw Heading Compass Tape (Top)
        self.draw_heading_tape(painter, w, h)

        # 5. Draw Depth Ladder Tape (Right)
        self.draw_depth_tape(painter, w, h)

        # 6. Draw EKF Current Vector Arrow (Bottom Left)
        self.draw_current_vector(painter, w, h)

    def draw_horizon(self, painter: QtGui.QPainter, cx: float, cy: float, w: int, h: int):
        painter.save()
        # Clip to central HUD region
        painter.setClipRect(40, 35, w - 100, h - 45)

        painter.translate(cx, cy)
        painter.rotate(-self.roll)

        # Pitch scale: 1 degree = 3.5 pixels
        pitch_offset = self.pitch * 3.5
        painter.translate(0, pitch_offset)

        diag = math.sqrt(w * w + h * h) * 1.5

        # Sky / Water surface gradient
        sky_grad = QtGui.QLinearGradient(0, -diag, 0, 0)
        sky_grad.setColorAt(0.0, QtGui.QColor(10, 45, 80))
        sky_grad.setColorAt(1.0, QtGui.QColor(25, 95, 140))
        painter.fillRect(int(-diag), int(-diag), int(diag * 2), int(diag), QtGui.QBrush(sky_grad))

        # Ground / Submerged gradient
        ground_grad = QtGui.QLinearGradient(0, 0, 0, diag)
        ground_grad.setColorAt(0.0, QtGui.QColor(15, 30, 45))
        ground_grad.setColorAt(1.0, QtGui.QColor(5, 12, 20))
        painter.fillRect(int(-diag), 0, int(diag * 2), int(diag), QtGui.QBrush(ground_grad))

        # Horizon Dividing Line
        pen = QtGui.QPen(self.horizon_line, 2)
        painter.setPen(pen)
        painter.drawLine(int(-diag), 0, int(diag), 0)

        painter.restore()

    def draw_pitch_ladder(self, painter: QtGui.QPainter, cx: float, cy: float, w: int, h: int):
        painter.save()
        painter.setClipRect(40, 35, w - 100, h - 45)
        painter.translate(cx, cy)
        painter.rotate(-self.roll)

        pitch_offset = self.pitch * 3.5
        painter.translate(0, pitch_offset)

        painter.setPen(QtGui.QPen(self.pitch_ladder_color, 1.5))
        font = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold)
        painter.setFont(font)

        # Draw pitch rungs (-30 to +30 deg with 5 deg increments)
        for deg in range(-30, 35, 5):
            if deg == 0:
                continue
            y = -deg * 3.5
            bar_w = 40 if deg % 10 == 0 else 20
            # Left bar
            painter.drawLine(int(-bar_w - 15), int(y), int(-15), int(y))
            # Right bar
            painter.drawLine(int(15), int(y), int(bar_w + 15), int(y))

            if deg % 10 == 0:
                # Vertical tick marks
                tick_dir = 5 if deg > 0 else -5
                painter.drawLine(int(-bar_w - 15), int(y), int(-bar_w - 15), int(y + tick_dir))
                painter.drawLine(int(bar_w + 15), int(y), int(bar_w + 15), int(y + tick_dir))
                # Deg text
                painter.drawText(int(bar_w + 20), int(y + 4), f"{abs(deg)}")

        painter.restore()

    def draw_aircraft_reticle(self, painter: QtGui.QPainter, cx: float, cy: float):
        painter.save()
        pen = QtGui.QPen(QtGui.QColor(255, 204, 0), 2.5)  # Amber Tactical Reticle
        painter.setPen(pen)

        # Center dot
        painter.drawEllipse(QtCore.QPointF(cx, cy), 3, 3)

        # Wing bars
        painter.drawLine(int(cx - 35), int(cy), int(cx - 10), int(cy))
        painter.drawLine(int(cx - 10), int(cy), int(cx - 10), int(cy + 6))

        painter.drawLine(int(cx + 10), int(cy), int(cx + 35), int(cy))
        painter.drawLine(int(cx + 10), int(cy), int(cx + 10), int(cy + 6))
        painter.restore()

    def draw_heading_tape(self, painter: QtGui.QPainter, w: int, h: int):
        tape_h = 32
        tape_w = w - 100
        tape_x = 40
        tape_y = 5

        painter.save()
        # Background
        painter.fillRect(tape_x, tape_y, tape_w, tape_h, self.tape_bg)
        painter.setPen(QtGui.QPen(QtGui.QColor(48, 54, 61), 1))
        painter.drawRect(tape_x, tape_y, tape_w, tape_h)

        # Clip inside tape
        painter.setClipRect(tape_x, tape_y, tape_w, tape_h)

        center_x = tape_x + tape_w / 2.0
        deg_spacing = 3.5  # px per degree

        font = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold)
        painter.setFont(font)

        # Draw graduation ticks (-40 deg to +40 deg from current yaw)
        for offset in range(-45, 46):
            target_deg = (int(self.yaw) + offset) % 360
            x = center_x + offset * deg_spacing

            if target_deg % 10 == 0:
                painter.setPen(QtGui.QPen(QtGui.QColor(240, 246, 252), 1.5))
                painter.drawLine(int(x), tape_y + tape_h - 12, int(x), tape_y + tape_h)

                label = f"{target_deg:03d}"
                if target_deg == 0: label = "N"
                elif target_deg == 90: label = "E"
                elif target_deg == 180: label = "S"
                elif target_deg == 270: label = "W"

                color = QtGui.QColor(255, 204, 0) if label in ("N", "E", "S", "W") else QtGui.QColor(240, 246, 252)
                painter.setPen(color)
                painter.drawText(int(x - 10), tape_y + 14, 20, 12, QtCore.Qt.AlignCenter, label)
            elif target_deg % 5 == 0:
                painter.setPen(QtGui.QPen(QtGui.QColor(139, 148, 158), 1))
                painter.drawLine(int(x), tape_y + tape_h - 6, int(x), tape_y + tape_h)

        # Center Indicator Triangle (Yaw Pointer)
        painter.restore()
        painter.save()
        center_x = tape_x + tape_w / 2.0
        poly = QtGui.QPolygonF([
            QtCore.QPointF(center_x - 6, tape_y + tape_h),
            QtCore.QPointF(center_x + 6, tape_y + tape_h),
            QtCore.QPointF(center_x, tape_y + tape_h + 6)
        ])
        painter.setBrush(QtGui.QColor(52, 168, 83))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPolygon(poly)

        # Current Heading Box
        painter.fillRect(int(center_x - 22), tape_y + 2, 44, 16, QtGui.QColor(42, 47, 56))
        painter.setPen(QtGui.QPen(QtGui.QColor(52, 168, 83), 1))
        painter.drawRect(int(center_x - 22), tape_y + 2, 44, 16)
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
        painter.drawText(int(center_x - 22), tape_y + 2, 44, 16, QtCore.Qt.AlignCenter, f"{int(self.yaw)}°")
        painter.restore()

    def draw_depth_tape(self, painter: QtGui.QPainter, w: int, h: int):
        tape_w = 55
        tape_h = h - 50
        tape_x = w - tape_w - 5
        tape_y = 40

        painter.save()
        # Background
        painter.fillRect(tape_x, tape_y, tape_w, tape_h, self.tape_bg)
        painter.setPen(QtGui.QPen(QtGui.QColor(48, 54, 61), 1))
        painter.drawRect(tape_x, tape_y, tape_w, tape_h)

        # Clip
        painter.setClipRect(tape_x, tape_y, tape_w, tape_h)

        center_y = tape_y + tape_h / 2.0
        depth_scale = 80.0  # px per meter

        font = QtGui.QFont("Segoe UI", 8)
        painter.setFont(font)

        # Draw depth graduations (0.1m increments)
        # In underwater: Depth increases going downward
        min_depth = max(0.0, self.depth - 1.5)
        max_depth = self.depth + 1.5

        # Major ticks every 0.5 m, minor every 0.1 m
        start_dec = int(min_depth * 10)
        end_dec = int(max_depth * 10)

        for d_int in range(start_dec, end_dec + 1):
            d_val = d_int / 10.0
            y = center_y + (d_val - self.depth) * depth_scale

            if d_int % 5 == 0:
                painter.setPen(QtGui.QPen(QtGui.QColor(240, 246, 252), 1.5))
                painter.drawLine(tape_x, int(y), tape_x + 12, int(y))
                painter.setPen(QtGui.QColor(240, 246, 252))
                painter.drawText(tape_x + 16, int(y - 6), 35, 12, QtCore.Qt.AlignLeft, f"{d_val:.1f}m")
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor(139, 148, 158), 1))
                painter.drawLine(tape_x, int(y), tape_x + 6, int(y))

        # Target Depth Marker Bug
        if self.target_depth > 0.05:
            target_y = center_y + (self.target_depth - self.depth) * depth_scale
            target_poly = QtGui.QPolygonF([
                QtCore.QPointF(tape_x, target_y),
                QtCore.QPointF(tape_x + 10, target_y - 6),
                QtCore.QPointF(tape_x + 10, target_y + 6)
            ])
            painter.setBrush(QtGui.QColor(255, 153, 0))  # Orange target bug
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawPolygon(target_poly)

        # Center Current Depth Readout Box
        painter.restore()
        painter.save()
        box_h = 24
        box_y = int(center_y - box_h / 2.0)
        painter.fillRect(tape_x - 10, box_y, tape_w + 10, box_h, QtGui.QColor(52, 168, 83))
        painter.setPen(QtGui.QPen(QtGui.QColor(46, 160, 67), 1))
        painter.drawRect(tape_x - 10, box_y, tape_w + 10, box_h)

        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
        painter.drawText(tape_x - 8, box_y, tape_w + 8, box_h, QtCore.Qt.AlignCenter, f"{self.depth:.2f}m")

        # Top label
        painter.setPen(QtGui.QColor(74, 144, 217))
        painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
        painter.drawText(tape_x, tape_y - 4, "DEPTH")
        painter.restore()

    def draw_current_vector(self, painter: QtGui.QPainter, w: int, h: int):
        """Draws EKF estimated current disturbance vector overlay."""
        mag = math.sqrt(self.disturb_surge ** 2 + self.disturb_sway ** 2)
        if mag < 0.05:
            return

        painter.save()
        bx = 60
        by = h - 35

        painter.fillRect(bx - 10, by - 20, 110, 45, QtGui.QColor(26, 29, 35, 200))
        painter.setPen(QtGui.QPen(QtGui.QColor(74, 144, 217), 1))
        painter.drawRect(bx - 10, by - 20, 110, 45)

        painter.setPen(QtGui.QColor(74, 144, 217))
        painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
        painter.drawText(bx - 5, by - 5, "EKF CURRENT")

        painter.setPen(QtGui.QColor(232, 234, 237))
        painter.setFont(QtGui.QFont("Segoe UI", 8))
        painter.drawText(bx - 5, by + 12, f"|d̂| = {mag:.2f} N")

        # Draw vector arrow
        angle = math.atan2(self.disturb_sway, self.disturb_surge)
        arrow_len = min(25, mag * 8)
        ex = bx + 75 + arrow_len * math.sin(angle)
        ey = by + 3 - arrow_len * math.cos(angle)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 204, 0), 2))
        painter.drawLine(int(bx + 75), int(by + 3), int(ex), int(ey))
        painter.restore()
