# -*- coding: utf-8 -*-
"""
Mock Teensy Server for Calibration Suite
Allows full offline testing of GUI Kalibrasi with realistic physics, noise,
and calibration command responses without requiring physical hardware.
"""

import math
import random
import socket
import threading
import time


class MockCalibrationServer:
    def __init__(self, host="127.0.0.1", port=9001):
        self.host = host
        self.port = port
        self.running = False
        self.server_sock = None
        self.client_sock = None
        self._thread = None

        # Simulated Sensor States
        self.ph = 7.02
        self.ec = 1412.0
        self.do_val = 6.25
        self.temp = 26.8
        self.roll = 0.15
        self.pitch = -0.22
        self.yaw = 184.5
        self.depth = 0.03
        self.press = 1013.25

        # Calibration Offset States
        self.ph_offset = 0.0
        self.gyro_bias = {"x": 0.05, "y": -0.04, "z": 0.02}
        self.depth_tare = 1013.25
        self.fluid_density = 997.0

        # Streaming flags
        self.stream_mag_raw = False

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self.stream_mag_raw = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

    def _run_server(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(1)
            self.server_sock.settimeout(1.0)
        except Exception as e:
            print(f"[MOCK SERVER] Bind error: {e}")
            self.running = False
            return

        while self.running:
            try:
                client, addr = self.server_sock.accept()
                self.client_sock = client
                self.client_sock.settimeout(0.2)
                self._handle_client(self.client_sock)
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, client: socket.socket):
        # Thread for receiving commands
        rx_thread = threading.Thread(target=self._client_rx_loop, args=(client,), daemon=True)
        rx_thread.start()

        step = 0
        mag_angle = 0.0

        while self.running and self.client_sock == client:
            try:
                step += 1
                t_now = int(time.time() * 1000)

                # Sensor micro-fluctuations (simulate noise & settling)
                ph_noise = random.uniform(-0.008, 0.008)
                ec_noise = random.uniform(-1.5, 1.5)
                do_noise = random.uniform(-0.02, 0.02)
                temp_noise = random.uniform(-0.01, 0.01)

                cur_ph = self.ph + ph_noise + self.ph_offset
                cur_ec = self.ec + ec_noise
                cur_do = self.do_val + do_noise
                cur_temp = self.temp + temp_noise

                # Motion micro-jitter
                cur_roll = self.roll + random.uniform(-0.05, 0.05)
                cur_pitch = self.pitch + random.uniform(-0.05, 0.05)
                cur_yaw = (self.yaw + 0.02) % 360.0
                cur_depth = max(0.0, (self.press - self.depth_tare) * 100.0 / (self.fluid_density * 9.80665))

                # Extended line: CAL_RT,ts,ph,ec,do,temp,roll,pitch,yaw,depth,press
                packet = (
                    f"CAL_RT,{t_now},"
                    f"{cur_ph:.3f},{cur_ec:.1f},{cur_do:.3f},{cur_temp:.2f},"
                    f"{cur_roll:.2f},{cur_pitch:.2f},{cur_yaw:.2f},{cur_depth:.3f},{self.press:.2f}\n"
                )
                client.sendall(packet.encode("utf-8"))

                # Stream Magnetometer samples if active
                if self.stream_mag_raw:
                    mag_angle += 0.15
                    # Ellipsoid simulation with hard-iron offset (15, -25) and scale stretch
                    bx = 35.0 * math.cos(mag_angle) + 18.0 + random.uniform(-1.0, 1.0)
                    by = 28.0 * math.sin(mag_angle) - 22.0 + random.uniform(-1.0, 1.0)
                    bz = 12.0 * math.sin(mag_angle * 0.5) + random.uniform(-0.8, 0.8)
                    mag_pkt = f"CAL_MAG_RAW,{bx:.2f},{by:.2f},{bz:.2f}\n"
                    client.sendall(mag_pkt.encode("utf-8"))

                time.sleep(0.1)  # 10 Hz rate
            except (socket.error, BrokenPipeError):
                break
            except Exception:
                break

        if self.client_sock == client:
            self.client_sock = None

    def _client_rx_loop(self, client: socket.socket):
        buf = ""
        while self.running and self.client_sock == client:
            try:
                chunk = client.recv(1024).decode("utf-8", errors="ignore")
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    cmd, buf = buf.split("\n", 1)
                    cmd = cmd.strip()
                    if cmd:
                        self._process_command(client, cmd)
            except socket.timeout:
                continue
            except Exception:
                break

    def _process_command(self, client: socket.socket, cmd: str):
        parts = cmd.split(",")
        header = parts[0].upper()

        resp = None

        # pH Calibration
        if header == "CAL_PH":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "mid":
                val = parts[2] if len(parts) > 2 else "7.00"
                self.ph = float(val)
                resp = f"CAL_RESP,PH,*OK,Mid Calibrated to {val} (Offset: 0.012)\n"
            elif sub == "low":
                val = parts[2] if len(parts) > 2 else "4.00"
                resp = f"CAL_RESP,PH,*OK,Low Calibrated to {val} (Acid Slope: 98.6%)\n"
            elif sub == "high":
                val = parts[2] if len(parts) > 2 else "10.00"
                resp = f"CAL_RESP,PH,*OK,High Calibrated to {val} (Base Slope: 99.2%)\n"
            elif sub == "?":
                resp = "CAL_RESP,PH,?CAL,3 (Mid, Low, High Active)\n"
            elif sub == "clear":
                self.ph_offset = 0.0
                resp = "CAL_RESP,PH,*OK,Factory Calibration Restored\n"

        # EC Calibration
        elif header == "CAL_EC":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "dry":
                self.ec = 0.0
                resp = "CAL_RESP,EC,*OK,Dry Zero Offset Saved (0.0 uS/cm)\n"
            elif sub == "one":
                val = parts[2] if len(parts) > 2 else "1413"
                self.ec = float(val)
                resp = f"CAL_RESP,EC,*OK,Single Point {val} uS/cm Calibrated\n"
            elif sub == "low":
                val = parts[2] if len(parts) > 2 else "12880"
                self.ec = float(val)
                resp = f"CAL_RESP,EC,*OK,Low Range {val} uS/cm Calibrated\n"
            elif sub == "high":
                val = parts[2] if len(parts) > 2 else "80000"
                self.ec = float(val)
                resp = f"CAL_RESP,EC,*OK,High Range {val} uS/cm Calibrated\n"
            elif sub == "?":
                resp = "CAL_RESP,EC,?CAL,2 (Dry, Single 1413 Active)\n"
            elif sub == "clear":
                self.ec = 1412.0
                resp = "CAL_RESP,EC,*OK,Factory EC Restored\n"

        # DO Calibration
        elif header == "CAL_DO":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "sat":
                resp = "CAL_RESP,DO,*OK,100% Saturation Voltage Recorded: 1612 mV\n"
            elif sub == "zero":
                resp = "CAL_RESP,DO,*OK,Zero Point (0 mg/L) Recorded: 14 mV\n"
            elif sub == "clear":
                resp = "CAL_RESP,DO,*OK,DO Factory Defaults Restored\n"

        # Temperature Calibration (Atlas Scientific Surveyor RTD PT-1000)
        elif header == "CAL_TEMP":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "ice":
                self.temp = 0.0
                resp = "CAL_RESP,TEMP,*OK,Ice Bath 0.0C Offset Recorded: 1058 mV (V0=1.058V)\n"
            elif sub == "cal":
                target_val = float(parts[2]) if len(parts) > 2 else 25.0
                v_calc = 1.058 + (0.009 * target_val)
                self.temp = target_val
                resp = f"CAL_RESP,TEMP,*OK,Calibrated at {target_val:.2f} C (V_meas: {v_calc:.3f}V)\n"
            elif sub == "?":
                resp = "CAL_RESP,TEMP,?CAL,1 (Surveyor RTD V0=1.058V, Slope=9.0mV/C Active)\n"
            elif sub == "clear":
                self.temp = 26.8
                resp = "CAL_RESP,TEMP,*OK,Surveyor RTD Factory Defaults Restored (V0=1.058V, Slope=0.009V/C)\n"

        # IMU Gyro & Leveling
        elif header == "CAL_IMU":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "gyro":
                self.gyro_bias = {"x": 0.0, "y": 0.0, "z": 0.0}
                resp = "CAL_RESP,IMU,*OK,Gyro Zero-Bias Calibrated (X: 0.00, Y: 0.00, Z: 0.00 deg/s)\n"
            elif sub == "level":
                self.roll = 0.0
                self.pitch = 0.0
                resp = "CAL_RESP,IMU,*OK,Horizon Level Tare Set (Roll: 0.00, Pitch: 0.00 deg)\n"

        # Magnetometer
        elif header == "CAL_MAG":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "start":
                self.stream_mag_raw = True
                resp = "CAL_RESP,MAG,*OK,Raw 3D Magnetic Stream Started\n"
            elif sub == "stop":
                self.stream_mag_raw = False
                resp = "CAL_RESP,MAG,*OK,Raw 3D Magnetic Stream Stopped\n"
            elif sub == "save":
                self.stream_mag_raw = False
                resp = "CAL_RESP,MAG,*OK,Hard/Soft-Iron Correction Matrix Saved to EEPROM\n"

        # Depth / Pressure
        elif header == "CAL_DEPTH":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "tare":
                self.depth_tare = self.press
                self.depth = 0.00
                resp = f"CAL_RESP,DEPTH,*OK,Surface Zero Tare: {self.press:.2f} mbar -> Depth 0.000 m\n"
            elif sub == "density":
                if len(parts) > 2:
                    try:
                        self.fluid_density = float(parts[2])
                        resp = f"CAL_RESP,DEPTH,*OK,Fluid Density Set: {self.fluid_density:.1f} kg/m3\n"
                    except ValueError:
                        resp = "CAL_RESP,DEPTH,ERROR,Invalid density value\n"

        if resp:
            try:
                client.sendall(resp.encode("utf-8"))
            except Exception:
                pass
