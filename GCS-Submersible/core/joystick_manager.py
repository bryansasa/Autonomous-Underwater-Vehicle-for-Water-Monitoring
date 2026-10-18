# -*- coding: utf-8 -*-
"""
Joystick & Gamepad Input Manager for Submersible GCS
Translates physical controller inputs into 4 DoF motion commands (Surge, Sway, Heave, Yaw).
"""
import os
from typing import Optional, Dict
from PyQt5 import QtCore

try:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    pygame = None
    PYGAME_AVAILABLE = False


class JoystickManager(QtCore.QObject):
    """
    Polls connected gamepad at 20-50 Hz and emits 4 DoF control signals.
    """
    motion_command_emitted = QtCore.pyqtSignal(int, int, int, int)  # surge, sway, heave, yaw (-400 to +400)
    button_pressed_emitted = QtCore.pyqtSignal(int)  # button id
    status_changed_emitted = QtCore.pyqtSignal(bool, str)

    def __init__(self, deadzone: float = 0.15, max_speed: int = 400):
        super().__init__()
        self.deadzone = deadzone
        self.max_speed = max_speed
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.is_initialized = False

        self.last_surge = 0
        self.last_sway = 0
        self.last_heave = 0
        self.last_yaw = 0

        self.poll_timer = QtCore.QTimer()
        self.poll_timer.timeout.connect(self.poll_controller)

    def initialize(self) -> bool:
        if not PYGAME_AVAILABLE:
            self.status_changed_emitted.emit(False, "Pygame is not installed")
            return False

        try:
            pygame.init()
            pygame.joystick.init()
            count = pygame.joystick.get_count()
            if count > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                name = self.joystick.get_name()
                self.is_initialized = True
                self.status_changed_emitted.emit(True, f"Controller Connected: {name}")
                self.poll_timer.start(50)  # 20 Hz
                return True
            else:
                self.status_changed_emitted.emit(False, "No Gamepad Detected")
                return False
        except Exception as e:
            self.status_changed_emitted.emit(False, f"Init Error: {e}")
            return False

    def set_max_speed(self, speed: int):
        self.max_speed = max(50, min(1000, speed))

    def _apply_deadzone(self, raw_val: float) -> float:
        if abs(raw_val) < self.deadzone:
            return 0.0
        # Normalize range outside deadzone to 0.0 - 1.0
        sign = 1.0 if raw_val > 0 else -1.0
        normalized = (abs(raw_val) - self.deadzone) / (1.0 - self.deadzone)
        return sign * min(1.0, normalized)

    def poll_controller(self):
        if not self.is_initialized or not self.joystick:
            return

        try:
            pygame.event.pump()

            # Axis Mappings (Standard Xbox/PS4 layout)
            # Axis 0: Left Stick X (Sway)
            # Axis 1: Left Stick Y (Surge - Inverted: -1 is Forward)
            # Axis 2 / 3: Right Stick X (Yaw)
            # Axis 3 / 4: Right Stick Y (Heave - Inverted: -1 is Ascend)

            raw_sway = self.joystick.get_axis(0)
            raw_surge = -self.joystick.get_axis(1)

            num_axes = self.joystick.get_num_axes()
            raw_yaw = self.joystick.get_axis(2 if num_axes > 2 else 0)
            raw_heave = -self.joystick.get_axis(3 if num_axes > 3 else 1)

            # Apply Deadzones
            val_surge = int(self._apply_deadzone(raw_surge) * self.max_speed)
            val_sway = int(self._apply_deadzone(raw_sway) * self.max_speed)
            val_heave = int(self._apply_deadzone(raw_heave) * self.max_speed)
            val_yaw = int(self._apply_deadzone(raw_yaw) * self.max_speed)

            # Emit only if there's any active movement or state changed
            if (val_surge != self.last_surge or val_sway != self.last_sway or
                    val_heave != self.last_heave or val_yaw != self.last_yaw):
                self.last_surge = val_surge
                self.last_sway = val_sway
                self.last_heave = val_heave
                self.last_yaw = val_yaw
                self.motion_command_emitted.emit(val_surge, val_sway, val_heave, val_yaw)

            # Check Button Press Events
            num_buttons = self.joystick.get_num_buttons()
            for b in range(num_buttons):
                if self.joystick.get_button(b):
                    self.button_pressed_emitted.emit(b)

        except Exception:
            pass
