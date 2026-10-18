# -*- coding: utf-8 -*-
"""
Telemetry Parser Module for Tyrant-AQ AUV GCS
Supports Legacy and Extended Submersible Telemetry Protocols.
"""
from typing import Optional, Dict, Any


class TelemetryParser:
    """
    Parses raw data streams from Teensy 4.1 MCU into structured dictionaries.
    """

    @staticmethod
    def is_valid_number(val: Any) -> bool:
        if val is None:
            return False
        s = str(val).strip()
        if s == "" or s.upper() in ("NAN", "N/A", "NONE"):
            return False
        try:
            float(s)
            return True
        except ValueError:
            return False

    @staticmethod
    def safe_float(val: Any, default: float = 0.0) -> float:
        try:
            if TelemetryParser.is_valid_number(val):
                return float(val)
        except Exception:
            pass
        return default

    @staticmethod
    def safe_int(val: Any, default: int = 0) -> int:
        try:
            if TelemetryParser.is_valid_number(val):
                return int(float(val))
        except Exception:
            pass
        return default

    @classmethod
    def parse_rt_line(cls, line: str) -> Optional[Dict[str, Any]]:
        """
        Parses real-time telemetry line starting with 'RT,'.
        Supports both legacy formats (9 to 26 fields) and new 32+ field extended format.
        """
        parts = [x.strip() for x in line.split(",")]
        if not parts or parts[0] != "RT":
            return None

        # Base dictionary with comprehensive default values
        data = {
            "header": "RT",
            "timestamp": 0,
            # Water Quality
            "temp": 0.0,
            "ph": 0.0,
            "do": 0.0,
            "cond": 0.0,
            # Power & Battery 1: Thrusters & ESC (INA226 #1, 6S LiPo)
            "battery_v": 0.0,
            "current_a": 0.0,
            "soc": 100.0,
            "soc_kalman": 100.0,
            "wea_penalty": 1.0,
            # Power & Battery 2: Electronics & Sensors (INA226 #2, 3S / Rail)
            "sensor_battery_v": 12.0,
            "sensor_current_a": 0.0,
            "sensor_soc": 100.0,
            # Motion & Navigation
            "depth": 0.0,
            "raw_pressure": 0.0,
            "target_depth": 0.0,
            "error_depth": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "target_yaw": 0.0,
            "error_yaw": 0.0,
            # EKF Observer & Current Disturbance
            "disturb_surge": 0.0,
            "disturb_sway": 0.0,
            "disturb_heave": 0.0,
            "disturb_yaw": 0.0,
            # LMPC Control Output & Execution Time
            "lmpc_wcet_ms": 0.0,
            "pid_output": 0.0,
            "virtual_force_surge": 0.0,
            "virtual_force_sway": 0.0,
            "virtual_force_heave": 0.0,
            "virtual_torque_yaw": 0.0,
            # Actuator PWM (6 Thrusters: 1100-1900 us)
            "pwm1": 1500,
            "pwm2": 1500,
            "pwm3": 1500,
            "pwm4": 1500,
            "pwm5": 1500,
            "pwm6": 1500,
            "pwm_main": 1500,
            # EA-DSRA & Dynamic Sampling Intervals (ms or s)
            "tbm_temp": 1.0,
            "tbm_ph": 1.0,
            "tbm_do": 1.0,
            "tbm_cond": 1.0,
            "power_gating_active": False,
            # Raw vs Reconstructed Signals
            "raw_temp": 0.0,
            "raw_ph": 0.0,
            "raw_do": 0.0,
            "raw_cond": 0.0,
            "sc_temp": 0.0,
            "sc_ph": 0.0,
            "sc_do": 0.0,
            "sc_cond": 0.0,
        }

        n = len(parts)

        # ----------------------------------------------------
        # Extended New Protocol (>= 32 parts)
        # Format: RT,ts,temp,ph,do,batt,curr,depth,cond,roll,pitch,yaw,
        #         pwm1,pwm2,pwm3,pwm4,pwm5,pwm6,
        #         tbm_temp,tbm_ph,tbm_do,tbm_cond,
        #         raw_temp,raw_ph,raw_do,raw_cond,raw_press,
        #         soc_k,wcet,d_surge,d_sway,d_heave,d_yaw
        # ----------------------------------------------------
        if n >= 32:
            data["timestamp"] = cls.safe_int(parts[1])
            data["temp"] = cls.safe_float(parts[2])
            data["ph"] = cls.safe_float(parts[3])
            data["do"] = cls.safe_float(parts[4])
            data["battery_v"] = cls.safe_float(parts[5])
            data["current_a"] = cls.safe_float(parts[6])
            data["depth"] = cls.safe_float(parts[7])
            data["cond"] = cls.safe_float(parts[8])

            data["roll"] = cls.safe_float(parts[9])
            data["pitch"] = cls.safe_float(parts[10])
            data["yaw"] = cls.safe_float(parts[11])

            data["pwm1"] = cls.safe_int(parts[12], 1500)
            data["pwm2"] = cls.safe_int(parts[13], 1500)
            data["pwm3"] = cls.safe_int(parts[14], 1500)
            data["pwm4"] = cls.safe_int(parts[15], 1500)
            data["pwm5"] = cls.safe_int(parts[16], 1500)
            data["pwm6"] = cls.safe_int(parts[17], 1500)
            data["pwm_main"] = data["pwm5"]  # Primary heave

            data["tbm_temp"] = cls.safe_float(parts[18])
            data["tbm_ph"] = cls.safe_float(parts[19])
            data["tbm_do"] = cls.safe_float(parts[20])
            data["tbm_cond"] = cls.safe_float(parts[21])

            data["raw_temp"] = cls.safe_float(parts[22], data["temp"])
            data["raw_ph"] = cls.safe_float(parts[23], data["ph"])
            data["raw_do"] = cls.safe_float(parts[24], data["do"])
            data["raw_cond"] = cls.safe_float(parts[25], data["cond"])
            data["raw_pressure"] = cls.safe_float(parts[26])

            data["soc_kalman"] = cls.safe_float(parts[27])
            data["soc"] = data["soc_kalman"]
            data["lmpc_wcet_ms"] = cls.safe_float(parts[28])
            data["disturb_surge"] = cls.safe_float(parts[29])
            data["disturb_sway"] = cls.safe_float(parts[30])
            data["disturb_heave"] = cls.safe_float(parts[31])
            if n >= 33:
                data["disturb_yaw"] = cls.safe_float(parts[32])
            if n >= 34:
                data["sensor_battery_v"] = cls.safe_float(parts[33], 12.0)
            if n >= 35:
                data["sensor_current_a"] = cls.safe_float(parts[34], 0.0)

            # Hitung estimasi SoC untuk Baterai Sensor & Mikrokontroler (3S LiPo: 9.9V - 12.6V)
            if data["sensor_battery_v"] > 5.0:
                v_s = data["sensor_battery_v"]
                data["sensor_soc"] = max(0.0, min(100.0, ((v_s - 9.9) / (12.6 - 9.9)) * 100.0))

        # ----------------------------------------------------
        # Legacy Extended Format (21 to 26 parts) from Program-WGG
        # ----------------------------------------------------
        elif n >= 21:
            data["timestamp"] = cls.safe_int(parts[1])
            data["temp"] = cls.safe_float(parts[2])
            data["ph"] = cls.safe_float(parts[3])
            data["do"] = cls.safe_float(parts[4])
            data["battery_v"] = cls.safe_float(parts[5])
            data["current_a"] = cls.safe_float(parts[6])
            data["depth"] = cls.safe_float(parts[7])
            data["cond"] = cls.safe_float(parts[8])

            data["error_depth"] = cls.safe_float(parts[9])
            data["pwm_main"] = cls.safe_int(parts[10], 1500)
            data["pwm5"] = data["pwm_main"]
            data["target_depth"] = cls.safe_float(parts[11])
            data["pid_output"] = cls.safe_float(parts[12])

            data["tbm_temp"] = cls.safe_float(parts[13])
            data["tbm_ph"] = cls.safe_float(parts[14])
            data["tbm_do"] = cls.safe_float(parts[15])
            data["tbm_cond"] = cls.safe_float(parts[16])

            data["raw_temp"] = cls.safe_float(parts[17], data["temp"])
            data["raw_ph"] = cls.safe_float(parts[18], data["ph"])
            data["raw_do"] = cls.safe_float(parts[19], data["do"])
            data["raw_cond"] = cls.safe_float(parts[20], data["cond"])

            if n >= 22:
                data["raw_pressure"] = cls.safe_float(parts[21])
            if n >= 26:
                data["sc_temp"] = cls.safe_float(parts[22])
                data["sc_ph"] = cls.safe_float(parts[23])
                data["sc_do"] = cls.safe_float(parts[24])
                data["sc_cond"] = cls.safe_float(parts[25])

        # ----------------------------------------------------
        # Legacy Intermediate Format (13 to 20 parts)
        # ----------------------------------------------------
        elif n >= 13:
            data["timestamp"] = cls.safe_int(parts[1])
            data["temp"] = cls.safe_float(parts[2])
            data["ph"] = cls.safe_float(parts[3])
            data["do"] = cls.safe_float(parts[4])
            data["battery_v"] = cls.safe_float(parts[5])
            data["current_a"] = cls.safe_float(parts[6])
            data["depth"] = cls.safe_float(parts[7])
            data["cond"] = cls.safe_float(parts[8])
            data["error_depth"] = cls.safe_float(parts[9])
            data["pwm_main"] = cls.safe_int(parts[10], 1500)
            data["pwm5"] = data["pwm_main"]
            data["target_depth"] = cls.safe_float(parts[11])
            data["pid_output"] = cls.safe_float(parts[12])

        # ----------------------------------------------------
        # Minimal Standard Format (9 to 12 parts)
        # ----------------------------------------------------
        elif n >= 9:
            data["timestamp"] = cls.safe_int(parts[1])
            data["temp"] = cls.safe_float(parts[2])
            data["ph"] = cls.safe_float(parts[3])
            data["do"] = cls.safe_float(parts[4])
            data["battery_v"] = cls.safe_float(parts[5])
            data["current_a"] = cls.safe_float(parts[6])
            data["depth"] = cls.safe_float(parts[7])
            data["cond"] = cls.safe_float(parts[8])

        # Fallback calculations if not provided
        if data["raw_temp"] == 0.0 and data["temp"] != 0.0:
            data["raw_temp"] = data["temp"]
        if data["raw_ph"] == 0.0 and data["ph"] != 0.0:
            data["raw_ph"] = data["ph"]
        if data["raw_do"] == 0.0 and data["do"] != 0.0:
            data["raw_do"] = data["do"]
        if data["raw_cond"] == 0.0 and data["cond"] != 0.0:
            data["raw_cond"] = data["cond"]

        # Calculate SoC if not provided via Kalman
        if data["soc_kalman"] == 100.0 and data["battery_v"] > 10.0:
            v_max = 25.2
            v_min = 19.8
            v_clamped = max(v_min, min(v_max, data["battery_v"]))
            data["soc"] = ((v_clamped - v_min) / (v_max - v_min)) * 100.0
            data["soc_kalman"] = data["soc"]

        return data
