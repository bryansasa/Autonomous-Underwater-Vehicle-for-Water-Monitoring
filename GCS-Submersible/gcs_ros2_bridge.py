#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS 2 & micro-ROS to GCS Bridge for Tyrant-AQ Autonomous Submersible
Integrasi Dual-Microcontroller:
  1. ESP32-S3 (micro-ROS Humble):
     - Sensor Kualitas Air (EZO pH, EZO EC, EZO DO, Temp RTD/DS18B20)
     - EA-DSRA Adaptive Sampling Rate Adaptation (T_BM 1.0 - 5.0 detik)
     - INA226 Power Monitor (Rel Sensor & Rel Thruster 6S LiPo Shunt 200A/75mV)
     - 4-Channel MOSFET Power Gating (EC=1, pH=2, Temp=3, DO=4)
     - Host Heartbeat Publisher (10 Hz pada /tyrant/payload/host_heartbeat)
  2. Teensy 4.1 (micro-ROS):
     - Navigasi & Orientasi 6-DOF (IMU WitMotion / Bar30 Depth Pressure)
     - Decoupled LMPC Station-Keeping & 6-Thruster Propulsion Matrix
     - Deadman Switch Manual Control (W/S/A/D/Panah)

Membuka TCP Server pada 0.0.0.0:9000 untuk dihubungkan ke GCS PyQt5 Dashboard.
Format Telemetri: 32-Field Extended ASCII ("RT,ts,temp,ph,do,batt,curr,depth,cond,...")
"""

import sys
import os
import time
import math
import socket
import threading
import argparse

# Cek ketersediaan pustaka ROS 2 (rclpy)
HAS_ROS2 = False
try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Float32, Float32MultiArray, Int16MultiArray, UInt32, Bool, String
    from sensor_msgs.msg import Imu, BatteryState
    from geometry_msgs.msg import Twist
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False

# Cek ketersediaan kustom interface Tyrant Payload (tyrant_payload_interfaces)
HAS_PAYLOAD_MSGS = False
try:
    from tyrant_payload_interfaces.msg import (
        PayloadWaterQuality,
        PayloadPower,
        PayloadHealth,
        PayloadCommunicationDiagnostics,
        SensorPowerRequest,
        SensorPowerStatus
    )
    HAS_PAYLOAD_MSGS = True
except ImportError:
    HAS_PAYLOAD_MSGS = False


class GCSBridge:
    def __init__(self, host="0.0.0.0", port=9000, is_mock=False, namespace="/tyrant/payload", is_sim=False):
        self.host = host
        self.port = port
        self.is_mock = is_mock
        self.namespace = "/tyrant/payload_sim" if is_sim else namespace
        self.running = True

        # State Telemetri Sensor Kualitas Air (ESP32-S3 Payload)
        self.timestamp = int(time.time() * 1000)
        self.temp = 27.20
        self.ph = 7.35
        self.do_val = 6.40
        self.cond = 315.0
        self.temp_valid = True
        self.ph_valid = True
        self.do_valid = True
        self.cond_valid = True
        self.last_wq_time = time.time()
        self.prev_wq_samples = {"ph": 7.35, "cond": 315.0, "temp": 27.20, "do": 6.40}

        # State Daya & Baterai (Dual INA226: Thruster 6S & Rel Sensor/MCU)
        self.battery_v = 24.80          # Baterai #1: Bus Thruster 6S LiPo (19.8V - 25.2V)
        self.v_filtered = 24.80         # Kalman-filtered voltage
        self.v_cov = 1.0                # Kalman covariance
        self.v_seen = False
        self.current_a = 2.10           # Thruster current (A)
        self.sensor_battery_v = 11.85   # Baterai #2: Rel Sensor & Mikrokontroler (9.9V - 12.6V)
        self.sensor_current_a = 0.22    # Sensor rail current (A)
        self.power_w = 52.0             # Total power (W)
        self.soc = 92.0                 # Battery SoC (%)
        self.soc_kalman = 92.0          # Kalman-filtered SoC (%)
        self.wea_penalty = 1.0          # EA-DSRA Energy Penalty Factor

        # State EA-DSRA Interval Adaptif (Detik per sensor)
        self.tbm_temp = 3.0
        self.tbm_ph = 5.0
        self.tbm_do = 2.0
        self.tbm_cond = 4.0
        self.t_ea_final = 2.0
        self.is_critical_do = False

        # State Status MOSFET & Diagnostik ESP32
        self.mosfet_status = {"EC": True, "PH": True, "TEMP": True, "DO": True}
        self.i2c_bus1_ok = True
        self.i2c_bus2_ok = True
        self.esp_connected = False
        self.hb_seq = 0

        # State Navigasi & Gerak Wahana (Teensy 4.1 Submersible)
        self.depth = 0.00
        self.target_depth = 1.00
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.pwm = [1500, 1500, 1500, 1500, 1500, 1500]
        self.disturb_surge = 0.0
        self.disturb_sway = 0.0
        self.disturb_heave = 0.0

        # TCP Server ke GCS
        self.tcp_server = None
        self.client_sock = None
        self._lock = threading.Lock()

        # ROS 2 Node references
        self.ros_node = None
        self.pub_host_hb = None
        self.pub_sensor_power = None
        self.pub_cmd_vel = None
        self.pub_setpoint = None
        self.pub_arm = None

    def start(self):
        print("=" * 70)
        print("  TYRANT-AQ AUV — ROS 2 & micro-ROS TO GCS BRIDGE v2.0")
        print(f"  TCP Server Listening : {self.host}:{self.port}")
        print(f"  ROS 2 Environment    : {'TERSEDIA (rclpy AKTIF)' if HAS_ROS2 else 'MOCK / SIMULASI WINDOWS'}")
        print(f"  Custom Interfaces    : {'tyrant_payload_interfaces OK' if HAS_PAYLOAD_MSGS else 'STANDAR FALLBACK (Belum di-source)'}")
        print(f"  Payload Namespace    : {self.namespace}")
        print("=" * 70)

        # 1. Jalankan TCP Server untuk GCS
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server.bind((self.host, self.port))
        self.tcp_server.listen(2)

        threading.Thread(target=self._tcp_listen_loop, daemon=True).start()
        threading.Thread(target=self._telemetry_stream_loop, daemon=True).start()

        # 2. Jalankan ROS 2 Node (Jika ROS 2 tersedia dan bukan mock)
        if HAS_ROS2 and not self.is_mock:
            self._start_ros2_node()
        else:
            print("[INFO] Menjalankan mode simulator internal data bridge...")
            self._start_mock_loop()

    # -------------------------------------------------------------------------
    # ROS 2 Node Setup & Callbacks
    # -------------------------------------------------------------------------
    def _start_ros2_node(self):
        rclpy.init()
        self.ros_node = Node("gcs_ros2_bridge")
        print(f"[ROS 2] Node 'gcs_ros2_bridge' aktif pada namespace '{self.namespace}'.")

        # ---------------------------------------------------------------------
        # A. Topik ESP32-S3 micro-ROS Payload & EA-DSRA
        # ---------------------------------------------------------------------
        ns = self.namespace.rstrip("/")

        # Host Heartbeat Publisher (Wajib 10 Hz ke ESP32-S3!)
        # ESP32 firmware memiliki timeout 1000 ms; jika host heartbeat mati, ESP menolak ON commands.
        self.pub_host_hb = self.ros_node.create_publisher(UInt32, f"{ns}/host_heartbeat", 10)
        self.ros_node.create_timer(0.1, self._timer_publish_host_heartbeat)

        # Sensor Power Request Publisher (Untuk kontrol MOSFET sensor ON/OFF)
        if HAS_PAYLOAD_MSGS:
            self.pub_sensor_power = self.ros_node.create_publisher(
                SensorPowerRequest, f"{ns}/sensor_power/request", 10
            )

        # Subscribers dari ESP32 Payload (Jika tyrant_payload_interfaces tersedia)
        if HAS_PAYLOAD_MSGS:
            self.ros_node.create_subscription(
                PayloadWaterQuality, f"{ns}/water_quality", self._cb_payload_wq, 10
            )
            self.ros_node.create_subscription(
                PayloadPower, f"{ns}/power/thruster", self._cb_payload_pwr_thruster, 10
            )
            self.ros_node.create_subscription(
                PayloadPower, f"{ns}/power/sensors", self._cb_payload_pwr_sensors, 10
            )
            self.ros_node.create_subscription(
                PayloadHealth, f"{ns}/health", self._cb_payload_health, 10
            )
            self.ros_node.create_subscription(
                SensorPowerStatus, f"{ns}/sensor_power/status", self._cb_payload_pwr_status, 10
            )
            self.ros_node.create_subscription(
                PayloadCommunicationDiagnostics, f"{ns}/communication/diagnostics", self._cb_payload_diag, 10
            )
            print(f"[ROS 2] Berlangganan topik Payload ESP32: {ns}/water_quality, {ns}/power/*, {ns}/health")
        else:
            print("[PERINGATAN] tyrant_payload_interfaces belum terbaca. Menggunakan topik standar /auv/*.")

        # Fallback water quality (Teensy atau skenario tanpa custom message)
        self.ros_node.create_subscription(Float32MultiArray, "/auv/water_quality", self._cb_legacy_wq, 10)
        self.ros_node.create_subscription(BatteryState, "/auv/power", self._cb_legacy_power, 10)

        # ---------------------------------------------------------------------
        # B. Topik Teensy 4.1 Submersible Navigasi, IMU, Depth & Thrusters
        # ---------------------------------------------------------------------
        self.ros_node.create_subscription(Imu, "/auv/imu", self._cb_imu, 10)
        self.ros_node.create_subscription(Float32, "/auv/depth", self._cb_depth, 10)
        self.ros_node.create_subscription(Int16MultiArray, "/auv/thrusters", self._cb_thrusters, 10)

        # Publisher Kontrol Gerak & Kedalaman ke Teensy LMPC
        self.pub_cmd_vel = self.ros_node.create_publisher(Twist, "/cmd_vel", 10)
        self.pub_setpoint = self.ros_node.create_publisher(Float32, "/auv/setpoint_depth", 10)
        self.pub_arm = self.ros_node.create_publisher(Bool, "/auv/arm_disarm", 10)

        print("[ROS 2] Menyiapkan publisher: /cmd_vel, /auv/setpoint_depth, /auv/arm_disarm")
        print("[ROS 2] Jembatan siap menerima streaming telemetri...")

        try:
            rclpy.spin(self.ros_node)
        except KeyboardInterrupt:
            pass
        finally:
            self.ros_node.destroy_node()
            rclpy.shutdown()

    # -------------------------------------------------------------------------
    # Callbacks: ESP32-S3 Payload & EA-DSRA
    # -------------------------------------------------------------------------
    def _timer_publish_host_heartbeat(self):
        """Memancarkan heartbeat host secara berkala 10 Hz ke ESP32-S3."""
        if self.pub_host_hb:
            msg = UInt32()
            msg.data = self.hb_seq
            self.pub_host_hb.publish(msg)
            self.hb_seq = (self.hb_seq + 1) & 0xFFFFFFFF

    def _cb_payload_wq(self, msg):
        """Menerima hasil akuisisi kualitas air adaptif EA-DSRA dari ESP32."""
        now = time.time()
        dt = max(0.001, now - self.last_wq_time)
        self.last_wq_time = now

        with self._lock:
            # Ambil nilai jika valid
            if msg.ph_valid:
                self.ph = float(msg.ph)
            if msg.conductivity_valid:
                self.cond = float(msg.conductivity_us_cm)
            if msg.dissolved_oxygen_valid:
                self.do_val = float(msg.dissolved_oxygen_mg_l)
            if msg.temperature_valid:
                self.temp = float(msg.temperature_c)

            self.ph_valid = bool(msg.ph_valid)
            self.cond_valid = bool(msg.conductivity_valid)
            self.do_valid = bool(msg.dissolved_oxygen_valid)
            self.temp_valid = bool(msg.temperature_valid)

            # Hitung gradien fluktuasi air S_max (EA-DSRA model)
            slope_ph = abs(self.ph - self.prev_wq_samples["ph"]) / dt
            slope_cond = abs(self.cond - self.prev_wq_samples["cond"]) / dt / 100.0
            slope_temp = abs(self.temp - self.prev_wq_samples["temp"]) / dt
            slope_do = abs(self.do_val - self.prev_wq_samples["do"]) / dt
            max_slope = max(slope_ph, slope_cond, slope_temp, slope_do)

            self.prev_wq_samples = {
                "ph": self.ph, "cond": self.cond, "temp": self.temp, "do": self.do_val
            }

            # Hitung T_BM DSRA dinamis (1.0 s s/d 5.0 s)
            tbm_proposed = max(1.0, min(5.0, 5.0 - 2.0 * max_slope))
            tbm_adjusted = max(1.0, min(5.0, tbm_proposed * self.wea_penalty))

            # Penanganan DO Kritis (<= 2.0 mg/L memaksa interval 1.0 detik)
            if self.do_valid and self.do_val <= 2.0:
                self.is_critical_do = True
                self.tbm_do = 1.0
                self.t_ea_final = 1.0
            else:
                self.is_critical_do = False
                self.tbm_do = tbm_adjusted
                self.t_ea_final = tbm_adjusted

            self.tbm_ph = min(5.0, tbm_adjusted * 1.2)
            self.tbm_temp = min(5.0, tbm_adjusted * 1.1)
            self.tbm_cond = min(5.0, tbm_adjusted * 1.15)

    def _cb_payload_pwr_thruster(self, msg):
        """Menerima tegangan dan arus bus thruster 6S LiPo dari INA226 kedua."""
        if not msg.valid:
            return

        v_raw = float(msg.bus_voltage_v)
        curr = float(msg.current_a)

        with self._lock:
            self.current_a = curr
            self.battery_v = v_raw

            # 1D Kalman Filter pada Tegangan Baterai (Sesuai implementasi ea_dsra.cpp)
            if not self.v_seen:
                self.v_filtered = v_raw
                self.v_cov = 1.0
                self.v_seen = True
            else:
                prior = self.v_cov + 1e-5
                gain = prior / (prior + 0.01)
                self.v_filtered += gain * (v_raw - self.v_filtered)
                self.v_cov = (1.0 - gain) * prior

            # Kalkulasi State of Charge (SoC %) untuk 6S LiPo (19.8V - 25.2V)
            v_min = 19.8
            v_max = 25.2
            self.soc_kalman = max(0.0, min(100.0, ((self.v_filtered - v_min) / (v_max - v_min)) * 100.0))
            self.soc = self.soc_kalman

            # Faktor Pembobotan Penalti Energi W_ea (Bila SoC <= 30%)
            if self.soc_kalman <= 30.0:
                self.wea_penalty = 30.0 / max(1.0, self.soc_kalman)
            else:
                self.wea_penalty = 1.0

            # Total Daya Sistem (P_total = P_thruster + P_sensor)
            self.power_w = (self.v_filtered * self.current_a) + (self.sensor_battery_v * self.sensor_current_a)

    def _cb_payload_pwr_sensors(self, msg):
        """Menerima tegangan dan arus rel sensor & mikrokontroler dari INA226 #2 (R100)."""
        if msg.valid:
            with self._lock:
                self.sensor_battery_v = float(msg.bus_voltage_v)
                self.sensor_current_a = float(msg.current_a)
                self.power_w = (self.v_filtered * self.current_a) + (self.sensor_battery_v * self.sensor_current_a)

    def _cb_payload_health(self, msg):
        """Menerima status kesehatan rel, I2C, dan perintah MOSFET."""
        with self._lock:
            self.mosfet_status["COND"] = bool(msg.mosfet_conductivity_on)
            self.mosfet_status["PH"] = bool(msg.mosfet_ph_on)
            self.mosfet_status["TEMP"] = bool(msg.mosfet_temperature_on)
            self.mosfet_status["DO"] = bool(msg.mosfet_do_on)
            self.i2c_bus1_ok = bool(msg.i2c_bus1_healthy)
            self.i2c_bus2_ok = bool(msg.i2c_bus2_healthy)

    def _cb_payload_pwr_status(self, msg):
        print(f"[ESP32 POWER ACK] Sensor #{msg.sensor_id} -> Requested={msg.requested_enable}, Accepted={msg.accepted}, Actual={msg.actual_enabled}")

    def _cb_payload_diag(self, msg):
        with self._lock:
            self.esp_connected = bool(msg.agent_connected)

    def _cb_legacy_wq(self, msg):
        """Fallback callback jika menerima Float32MultiArray standar."""
        if len(msg.data) >= 4:
            with self._lock:
                self.ph = float(msg.data[0])
                self.cond = float(msg.data[1])
                self.do_val = float(msg.data[2])
                self.temp = float(msg.data[3])

    def _cb_legacy_power(self, msg):
        """Fallback callback jika menerima BatteryState standar."""
        with self._lock:
            self.battery_v = float(msg.voltage)
            self.current_a = float(msg.current)
            self.soc = float(msg.percentage * 100.0 if msg.percentage <= 1.0 else msg.percentage)
            self.soc_kalman = self.soc

    # -------------------------------------------------------------------------
    # Callbacks: Teensy 4.1 Navigasi, IMU, Depth & Thrusters
    # -------------------------------------------------------------------------
    def _cb_imu(self, msg):
        q = msg.orientation
        sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll_deg = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        pitch_deg = math.degrees(math.asin(sinp)) if abs(sinp) <= 1.0 else math.copysign(90.0, sinp)

        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw_deg = math.degrees(math.atan2(siny_cosp, cosy_cosp)) % 360.0

        with self._lock:
            self.roll = roll_deg
            self.pitch = pitch_deg
            self.yaw = yaw_deg

    def _cb_depth(self, msg):
        with self._lock:
            self.depth = float(msg.data)

    def _cb_thrusters(self, msg):
        if len(msg.data) >= 6:
            with self._lock:
                self.pwm = [int(x) for x in msg.data[:6]]

    # -------------------------------------------------------------------------
    # TCP Server Communication ke GUI GCS
    # -------------------------------------------------------------------------
    def _tcp_listen_loop(self):
        while self.running:
            try:
                sock, addr = self.tcp_server.accept()
                with self._lock:
                    self.client_sock = sock
                print(f"[BRIDGE] GUI GCS Terhubung dari {addr}")
                threading.Thread(target=self._rx_gcs_loop, args=(sock,), daemon=True).start()
            except Exception:
                break

    def _rx_gcs_loop(self, sock: socket.socket):
        buf = ""
        while self.running and self.client_sock == sock:
            try:
                chunk = sock.recv(1024).decode("utf-8", errors="ignore")
                if not chunk:
                    break
                buf += chunk

                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._process_gcs_command(line)
            except Exception:
                break

        print("[BRIDGE] GUI GCS Terputus.")
        with self._lock:
            if self.client_sock == sock:
                self.client_sock = None

    def _process_gcs_command(self, cmd: str):
        parts = cmd.split(",")
        header = parts[0].upper()

        print(f"[BRIDGE RX dari GCS] {cmd}")

        # 1. Kontrol Gerak Manual (STICK,surge,sway,heave,yaw)
        if header == "STICK" and len(parts) >= 5:
            try:
                surge = float(parts[1])
                sway = float(parts[2])
                heave = float(parts[3])
                yaw = float(parts[4])
                if self.pub_cmd_vel:
                    twist = Twist()
                    twist.linear.x = surge
                    twist.linear.y = sway
                    twist.linear.z = heave
                    twist.angular.z = yaw
                    self.pub_cmd_vel.publish(twist)
            except ValueError:
                pass

        # 2. Setpoint Kedalaman LMPC (SETPOINT,depth)
        elif header == "SETPOINT" and len(parts) >= 2:
            try:
                sp_val = float(parts[1])
                with self._lock:
                    self.target_depth = sp_val
                if self.pub_setpoint:
                    msg = Float32()
                    msg.data = sp_val
                    self.pub_setpoint.publish(msg)
            except ValueError:
                pass

        # 3. Kontrol Daya Sensor MOSFET ke ESP32 (POWER,sensor_id,state)
        # ID: 1=EC/COND, 2=PH, 3=TEMP, 4=DO
        elif header in ("POWER", "PWR") and len(parts) >= 3:
            try:
                s_id = int(parts[1])
                enable = bool(int(parts[2]))
                if self.pub_sensor_power and HAS_PAYLOAD_MSGS:
                    req = SensorPowerRequest()
                    req.request_id = int(time.time() * 1000) & 0xFFFFFFFF
                    req.sensor_id = s_id
                    req.enable = enable
                    self.pub_sensor_power.publish(req)
                    print(f"[BRIDGE TX -> ESP32] SensorPowerRequest id={s_id} enable={enable}")
            except Exception as e:
                print(f"[BRIDGE ERROR] Gagal mengirim SensorPowerRequest: {e}")

        # 4. Arm / Disarm Wahana
        elif header == "ARM":
            if self.pub_arm:
                self.pub_arm.publish(Bool(data=True))
        elif header in ("DISARM", "KILL", "STOP_ALL"):
            if self.pub_arm:
                self.pub_arm.publish(Bool(data=False))
            if self.pub_cmd_vel:
                self.pub_cmd_vel.publish(Twist())

    # -------------------------------------------------------------------------
    # Telemetry Packet Formatter (Persis Sesuai TelemetryParser GCS 32-Field)
    # -------------------------------------------------------------------------
    def _telemetry_stream_loop(self):
        while self.running:
            if self.client_sock:
                try:
                    t_now = int(time.time() * 1000)
                    with self._lock:
                        # 32+ Fields Extended Format (RT,ts,temp,ph,do,batt,curr,depth,cond,roll,pitch,yaw,...)
                        pkt = (
                            f"RT,{t_now},"
                            f"{self.temp:.2f},{self.ph:.2f},{self.do_val:.2f},"
                            f"{self.battery_v:.2f},{self.current_a:.2f},{self.depth:.2f},{self.cond:.1f},"
                            f"{self.roll:.1f},{self.pitch:.1f},{self.yaw:.1f},"
                            f"{self.pwm[0]},{self.pwm[1]},{self.pwm[2]},{self.pwm[3]},{self.pwm[4]},{self.pwm[5]},"
                            f"{self.tbm_temp:.1f},{self.tbm_ph:.1f},{self.tbm_do:.1f},{self.tbm_cond:.1f},"
                            f"{self.temp:.2f},{self.ph:.2f},{self.do_val:.2f},{self.cond:.1f},1013.25,"
                            f"{self.soc_kalman:.1f},11.5,"
                            f"{self.disturb_surge:.2f},{self.disturb_sway:.2f},{self.disturb_heave:.2f},"
                            f"0.0,{self.sensor_battery_v:.2f},{self.sensor_current_a:.2f}\n"
                        )
                    self.client_sock.sendall(pkt.encode("utf-8"))
                except Exception:
                    with self._lock:
                        self.client_sock = None
            time.sleep(0.1)  # Frekuensi telemetri 10 Hz

    # -------------------------------------------------------------------------
    # Mock Loop (Jika dijalankan tanpa hardware / tanpa ROS 2 aktif)
    # -------------------------------------------------------------------------
    def _start_mock_loop(self):
        step = 0
        while self.running:
            step += 1
            with self._lock:
                # Simulasi gerak gelombang kecil & stasioner
                self.roll = 1.5 * math.sin(step * 0.05)
                self.pitch = 2.0 * math.cos(step * 0.04)
                self.yaw = (self.yaw + 0.3) % 360.0
                err = self.target_depth - self.depth
                self.depth += err * 0.04

                # Simulasi penurunan baterai lambat (Dual Battery)
                self.battery_v = max(19.8, self.battery_v - 0.0001)
                self.v_filtered = self.battery_v
                self.soc_kalman = max(0.0, min(100.0, ((self.battery_v - 19.8) / (25.2 - 19.8)) * 100.0))
                self.soc = self.soc_kalman
                self.sensor_battery_v = max(9.9, self.sensor_battery_v - 0.00003)

                # Penalti EA-DSRA
                if self.soc_kalman <= 30.0:
                    self.wea_penalty = 30.0 / max(1.0, self.soc_kalman)
                else:
                    self.wea_penalty = 1.0

                # Interval sampling dinamis
                self.tbm_ph = min(5.0, 5.0 * self.wea_penalty)
                self.tbm_do = min(5.0, 2.0 * self.wea_penalty)
                self.tbm_temp = min(5.0, 3.0 * self.wea_penalty)
                self.tbm_cond = min(5.0, 4.0 * self.wea_penalty)

            time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description="ROS 2 & micro-ROS to GCS Bridge (Tyrant-AQ)")
    parser.add_argument("--host", default="0.0.0.0", help="TCP Host bind address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9000, help="TCP Port (default 9000)")
    parser.add_argument("--namespace", default="/tyrant/payload", help="ESP32 Payload ROS namespace (default /tyrant/payload)")
    parser.add_argument("--sim", action="store_true", help="Gunakan namespace simulasi /tyrant/payload_sim")
    parser.add_argument("--mock", action="store_true", help="Jalankan mode mock dummy tanpa koneksi ROS 2")
    args = parser.parse_args()

    bridge = GCSBridge(
        host=args.host,
        port=args.port,
        is_mock=args.mock,
        namespace=args.namespace,
        is_sim=args.sim
    )
    try:
        bridge.start()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Menutup jembatan...")
        bridge.running = False


if __name__ == "__main__":
    main()
