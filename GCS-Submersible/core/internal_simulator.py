# -*- coding: utf-8 -*-
"""
Internal Simulation Engine for Tyrant-AQ AUV Ground Control Station.
Simulates full 6 Degrees of Freedom (6-DOF) Vehicle Dynamics:
  - 3 Linear Translations: Surge (Forward/Back), Sway (Left/Right), Heave (Up/Down)
  - 3 Angular Rotations: Roll (Tilt Left/Right), Pitch (Nose Up/Down), Yaw (Turn Left/Right)
  - Twin-Hull 6-Thruster Propulsion Matrix Mixing
  - Saguling Water Quality Stratification (pH, DO, Temperature, Conductivity vs Depth)
  - INA226 Battery & Kalman SoC model
"""
import time
import math
import random
import threading
from core.event_hook import EventHook


class InternalSimulator:
    """
    Simulates 6-DOF vehicle telemetry stream at 10 Hz without requiring physical hardware.
    Pure-Python implementation with zero GUI dependencies.
    """
    def __init__(self):
        self.telemetry_generated = EventHook()
        self.raw_packet_generated = EventHook()
        self.log_emitted = EventHook()
        self.running = False
        self._thread = None
        self._lock = threading.Lock()

        # Dynamic State Variables (Pose & Position)
        self.depth = 0.50          # Current depth (meters)
        self.target_depth = 1.50   # Target depth setpoint (meters)
        self.manual_active = False

        self.roll = 0.0            # degrees (-180 to 180)
        self.pitch = 0.0           # degrees (-90 to 90)
        self.yaw = 45.0            # degrees (0 to 360)
        self.target_yaw = 45.0

        # 6-DOF Normalized Control Demands (-1.0 to +1.0)
        self.cmd_surge = 0.0       # Forward (+) / Backward (-)
        self.cmd_sway = 0.0        # Strafe Right (+) / Strafe Left (-)
        self.cmd_heave = 0.0       # Descend (+) / Ascend (-)
        self.cmd_roll = 0.0        # Tilt Right (+) / Tilt Left (-)
        self.cmd_pitch = 0.0       # Nose Up (+) / Nose Down (-)
        self.cmd_yaw = 0.0         # Turn Right (+) / Turn Left (-)

        # Electrical / Power (Dual Battery Architecture)
        # Baterai 1: Thrusters & ESC (6S LiPo nominal ~25.2V max, ~19.8V min)
        self.battery_v = 24.80
        self.soc_kalman = 95.0
        self.current_a = 2.40
        # Baterai 2: Sensor & Mikrokontroler (3S LiPo ~12.6V max, ~9.9V min)
        self.sensor_battery_v = 12.10
        self.sensor_soc = 95.0
        self.sensor_current_a = 0.22

        # Water Quality (Saguling Baseline Profile)
        self.temp = 27.20
        self.ph = 7.45
        self.do_val = 6.20
        self.cond = 320.0

        # EA-DSRA adaptive parameters
        self.dsra_active = True
        self.tbm_temp = 3.0
        self.tbm_ph = 5.0
        self.tbm_do = 2.0
        self.tbm_cond = 4.0

        # Sensor power status
        self.sensor_power = {"DO": True, "PH": True, "COND": True, "TEMP": True}

        # Control Mode & Safety
        self.mode = "LMPC_AUTO"
        self.is_armed = True
        self.manual_speed_delta = 250  # PWM delta (50 - 400)

        # Thrusters PWM (1100 to 1900 us)
        self.pwms = [1500] * 6

    def start(self):
        if self.running:
            return
        self.running = True
        self.log_emitted.emit("[SIMULATOR] Engine Simulasi 6-DOF Tyrant-AQ AUV aktif (10 Hz).")
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None
        self.log_emitted.emit("[SIMULATOR] Engine Simulasi dinonaktifkan.")

    def process_command(self, cmd: str):
        """Receives and processes 6-DOF and system commands in simulation mode."""
        cmd = cmd.strip()
        if not cmd:
            return

        with self._lock:
            parts = cmd.split(",")
            header = parts[0].upper()

            # 1. Direct 6-DOF Vector Command
            if header == "DOF6":
                # DOF6,surge,sway,heave,roll,pitch,yaw
                if len(parts) >= 7:
                    try:
                        self.cmd_surge = float(parts[1])
                        self.cmd_sway = float(parts[2])
                        self.cmd_heave = float(parts[3])
                        self.cmd_roll = float(parts[4])
                        self.cmd_pitch = float(parts[5])
                        self.cmd_yaw = float(parts[6])
                    except ValueError:
                        pass

            # 2. Individual 6-DOF Axis Commands
            elif header == "SURGE":
                self.cmd_surge = float(parts[1]) if len(parts) > 1 else 0.0
            elif header == "SWAY":
                self.cmd_sway = float(parts[1]) if len(parts) > 1 else 0.0
            elif header == "HEAVE":
                self.cmd_heave = float(parts[1]) if len(parts) > 1 else 0.0
            elif header == "ROLL":
                self.cmd_roll = float(parts[1]) if len(parts) > 1 else 0.0
            elif header == "PITCH":
                self.cmd_pitch = float(parts[1]) if len(parts) > 1 else 0.0
            elif header == "YAW":
                self.cmd_yaw = float(parts[1]) if len(parts) > 1 else 0.0
            elif header == "STOP_ALL":
                self.cmd_surge = self.cmd_sway = self.cmd_heave = 0.0
                self.cmd_roll = self.cmd_pitch = self.cmd_yaw = 0.0

            # 3. Legacy Deadman W/S Commands (Ascend / Descend)
            elif header == "F":
                self.cmd_heave = -1.0
            elif header == "f":
                if self.cmd_heave < 0: self.cmd_heave = 0.0
            elif header == "B":
                self.cmd_heave = 1.0
            elif header == "b":
                if self.cmd_heave > 0: self.cmd_heave = 0.0

            # 4. Joystick Stick Command (surge, sway, heave, yaw)
            elif header == "STICK":
                if len(parts) >= 5:
                    try:
                        max_s = float(self.manual_speed_delta) or 250.0
                        self.cmd_surge = float(parts[1]) / max_s
                        self.cmd_sway = float(parts[2]) / max_s
                        self.cmd_heave = float(parts[3]) / max_s
                        self.cmd_yaw = float(parts[4]) / max_s
                    except ValueError:
                        pass

            # 5. Speed / PWM Delta Setting
            elif header == "SPEED":
                if len(parts) >= 2:
                    try:
                        self.manual_speed_delta = int(parts[1])
                    except ValueError:
                        pass

            # 6. Modes & Safety
            elif header == "MANUAL":
                self.manual_active = (parts[1].upper() == "ON") if len(parts) > 1 else False
                self.mode = "MANUAL" if self.manual_active else "LMPC_AUTO"
            elif header == "SETPOINT":
                if len(parts) >= 2:
                    try:
                        self.target_depth = max(0.0, float(parts[1]))
                    except ValueError:
                        pass
            elif header == "LMPC_CONTROL":
                state = parts[1].upper() if len(parts) > 1 else "OFF"
                self.mode = "LMPC_AUTO" if state == "ON" else "MANUAL"
            elif header == "ARM":
                self.is_armed = True
            elif header == "DISARM":
                self.is_armed = False
            elif header == "EMERGENCY_KILL":
                self.is_armed = False
                self.cmd_surge = self.cmd_sway = self.cmd_heave = 0.0
                self.cmd_roll = self.cmd_pitch = self.cmd_yaw = 0.0
                self.pwms = [1500] * 6
                self.log_emitted.emit("[SIMULATOR] Emergency Kill Switch dieksekusi!")
            elif header == "SENSOR":
                if len(parts) >= 3:
                    s_name = parts[1].upper()
                    s_state = (parts[2] == "1")
                    if s_name in self.sensor_power:
                        self.sensor_power[s_name] = s_state
            elif header == "DSRA_MODE":
                if len(parts) >= 2:
                    self.dsra_active = (parts[1] == "1")

    def _run_loop(self):
        step = 0
        while self.running:
            t_start = time.time()
            step += 1
            t_now_ms = int(time.time() * 1000)

            with self._lock:
                delta = self.manual_speed_delta

                # 1. 6-DOF Thruster Mixer (Twin-Hull 6 Thruster Configuration)
                if not self.is_armed:
                    pwm1 = pwm2 = pwm3 = pwm4 = pwm5 = pwm6 = 1500
                    # Slow buoyancy drift to surface if disarmed
                    self.depth = max(0.0, self.depth - 0.01)
                    self.roll += (0.0 - self.roll) * 0.05
                    self.pitch += (0.0 - self.pitch) * 0.05
                    depth_err = 0.0
                elif self.manual_active:
                    # Full 6-DOF Manual Mixing
                    # Horizontal Thrusters T1-T4 (Vector Thrusters @ 45 deg)
                    # Surge (Maju/Mundur), Sway (Geser Kanan/Kiri), Yaw (Putar Kanan/Kiri)
                    u_surge = self.cmd_surge * delta
                    u_sway = self.cmd_sway * delta
                    u_yaw = self.cmd_yaw * delta

                    pwm1 = int(1500 + (u_surge + u_sway + u_yaw))
                    pwm2 = int(1500 + (u_surge - u_sway - u_yaw))
                    pwm3 = int(1500 + (u_surge - u_sway + u_yaw))
                    pwm4 = int(1500 + (u_surge + u_sway - u_yaw))

                    # Vertical Thrusters T5-T6
                    # Heave (Turun/Naik), Roll (Miring Kanan/Kiri), Pitch (Nose Up/Down)
                    u_heave = self.cmd_heave * delta
                    u_roll = self.cmd_roll * delta
                    u_pitch = self.cmd_pitch * delta

                    pwm5 = int(1500 + (u_heave + u_roll + u_pitch))
                    pwm6 = int(1500 + (u_heave - u_roll + u_pitch))

                    # Update 6-DOF Pose from control inputs
                    self.depth = max(0.0, self.depth + self.cmd_heave * (delta / 400.0) * 0.08)
                    self.yaw = (self.yaw + self.cmd_yaw * (delta / 400.0) * 1.8) % 360.0
                    self.pitch = max(-60.0, min(60.0, self.pitch + self.cmd_pitch * (delta / 400.0) * 1.5))
                    self.roll = max(-60.0, min(60.0, self.roll + self.cmd_roll * (delta / 400.0) * 1.5))

                    # Natural hydrodynamic damping to restore level attitude when no pitch/roll input
                    if abs(self.cmd_pitch) < 0.05:
                        self.pitch += (0.0 - self.pitch) * 0.08
                    if abs(self.cmd_roll) < 0.05:
                        self.roll += (0.0 - self.roll) * 0.08

                    depth_err = self.target_depth - self.depth
                else:
                    # LMPC / PID Auto Station-Keeping Mode
                    depth_err = self.target_depth - self.depth
                    self.depth += depth_err * 0.06 + random.uniform(-0.005, 0.005)
                    self.depth = max(0.0, self.depth)
                    base_vert = int(1500 + depth_err * 140)

                    pwm5 = max(1100, min(1900, base_vert))
                    pwm6 = max(1100, min(1900, base_vert + random.randint(-4, 4)))
                    pwm1 = 1500 + random.randint(-25, 25)
                    pwm2 = 1500 + random.randint(-25, 25)
                    pwm3 = 1500 + random.randint(-25, 25)
                    pwm4 = 1500 + random.randint(-25, 25)

                    # Ambient wave oscillations
                    self.roll = 2.5 * math.sin(step * 0.04) + random.uniform(-0.15, 0.15)
                    self.pitch = 3.2 * math.cos(step * 0.035) + (depth_err * 2.0) + random.uniform(-0.15, 0.15)
                    self.yaw = (self.yaw + 0.12) % 360.0

                # Clamp PWM values to safe ESC range [1100, 1900]
                pwm1 = max(1100, min(1900, pwm1))
                pwm2 = max(1100, min(1900, pwm2))
                pwm3 = max(1100, min(1900, pwm3))
                pwm4 = max(1100, min(1900, pwm4))
                pwm5 = max(1100, min(1900, pwm5))
                pwm6 = max(1100, min(1900, pwm6))
                self.pwms = [pwm1, pwm2, pwm3, pwm4, pwm5, pwm6]

                # 2. Water Quality Stratification in Saguling Reservoir
                if self.sensor_power["TEMP"]:
                    self.temp = 27.80 - 0.45 * self.depth + random.uniform(-0.02, 0.02)
                else:
                    self.temp = 0.0

                if self.sensor_power["PH"]:
                    self.ph = 7.55 - 0.12 * self.depth + random.uniform(-0.015, 0.015)
                else:
                    self.ph = 0.0

                if self.sensor_power["DO"]:
                    self.do_val = max(1.0, 6.85 - 0.85 * self.depth + random.uniform(-0.04, 0.04))
                else:
                    self.do_val = 0.0

                if self.sensor_power["COND"]:
                    self.cond = 310.0 + 18.0 * self.depth + random.uniform(-0.8, 0.8)
                else:
                    self.cond = 0.0

                # 3. Battery & Power Consumption (Dual Battery System)
                # Baterai 1: Thruster 6S LiPo
                self.battery_v = max(19.8, self.battery_v - 0.00015)
                raw_v = self.battery_v + random.uniform(-0.08, 0.08)
                self.soc_kalman = max(0.0, min(100.0, ((self.battery_v - 19.8) / (25.2 - 19.8)) * 100.0))

                # Thruster active power draw (Arus Baterai 1)
                active_thrust = sum(abs(p - 1500) for p in self.pwms) / 1000.0
                self.current_a = 2.0 + active_thrust * 3.5 + random.uniform(-0.15, 0.15)

                # Baterai 2: Sensor & Mikrokontroler (3S LiPo 9.9V - 12.6V)
                self.sensor_battery_v = max(9.9, self.sensor_battery_v - 0.00004)
                sensor_v_raw = self.sensor_battery_v + random.uniform(-0.02, 0.02)
                self.sensor_soc = max(0.0, min(100.0, ((self.sensor_battery_v - 9.9) / (12.6 - 9.9)) * 100.0))
                sensor_pwr_count = sum(1 for v in self.sensor_power.values() if v)
                self.sensor_current_a = 0.08 + sensor_pwr_count * 0.035 + random.uniform(-0.005, 0.005)

                # 4. EKF Current Disturbance (Newtons)
                disturb_surge = 0.40 * math.sin(step * 0.02)
                disturb_sway = 0.28 * math.cos(step * 0.025)
                disturb_heave = 0.12 * math.sin(step * 0.015)

                # 5. Construct Telemetry Dictionary
                telemetry = {
                    "timestamp": t_now_ms,
                    "temp": round(self.temp, 2),
                    "ph": round(self.ph, 2),
                    "do": round(self.do_val, 2),
                    "battery_v": round(raw_v, 2),
                    "current_a": round(self.current_a, 2),
                    "sensor_battery_v": round(sensor_v_raw, 2),
                    "sensor_current_a": round(self.sensor_current_a, 2),
                    "sensor_soc": round(self.sensor_soc, 1),
                    "depth": round(self.depth, 2),
                    "target_depth": round(self.target_depth, 2),
                    "cond": round(self.cond, 1),
                    "roll": round(self.roll, 1),
                    "pitch": round(self.pitch, 1),
                    "yaw": round(self.yaw, 1),
                    "target_yaw": round(self.target_yaw, 1),
                    "pwms": self.pwms,
                    "pwm1": pwm1, "pwm2": pwm2, "pwm3": pwm3,
                    "pwm4": pwm4, "pwm5": pwm5, "pwm6": pwm6,
                    "tbm_temp": self.tbm_temp,
                    "tbm_ph": self.tbm_ph,
                    "tbm_do": self.tbm_do,
                    "tbm_cond": self.tbm_cond,
                    "raw_temp": round(self.temp, 2),
                    "raw_ph": round(self.ph, 2),
                    "raw_do": round(self.do_val, 2),
                    "raw_cond": round(self.cond, 1),
                    "raw_press": round(1013.25 + self.depth * 98.1, 1),
                    "soc_kalman": round(self.soc_kalman, 1),
                    "soc": round(self.soc_kalman, 1),
                    "lmpc_wcet": 11.4,
                    "disturb_surge": round(disturb_surge, 2),
                    "disturb_sway": round(disturb_sway, 2),
                    "disturb_heave": round(disturb_heave, 2),
                    "mode": self.mode,
                    "is_armed": self.is_armed,
                }

                # Raw packet string
                raw_pkt = (
                    f"RT,{t_now_ms},"
                    f"{self.temp:.2f},{self.ph:.2f},{self.do_val:.2f},{raw_v:.2f},{self.current_a:.2f},{self.depth:.2f},{self.cond:.1f},"
                    f"{self.roll:.1f},{self.pitch:.1f},{self.yaw:.1f},"
                    f"{pwm1},{pwm2},{pwm3},{pwm4},{pwm5},{pwm6},"
                    f"{self.tbm_temp:.1f},{self.tbm_ph:.1f},{self.tbm_do:.1f},{self.tbm_cond:.1f},"
                    f"{self.temp:.2f},{self.ph:.2f},{self.do_val:.2f},{self.cond:.1f},{1013.25 + self.depth * 98.1:.1f},"
                    f"{self.soc_kalman:.1f},11.4,"
                    f"{disturb_surge:.2f},{disturb_sway:.2f},{disturb_heave:.2f},"
                    f"0.0,{sensor_v_raw:.2f},{self.sensor_current_a:.2f}\n"
                )

            self.telemetry_generated.emit(telemetry)
            self.raw_packet_generated.emit(raw_pkt)

            # Enforce 10 Hz loop
            elapsed = time.time() - t_start
            sleep_time = max(0.01, 0.10 - elapsed)
            time.sleep(sleep_time)
