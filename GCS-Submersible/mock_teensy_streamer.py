# -*- coding: utf-8 -*-
"""
Mock Teensy 4.1 Telemetry Streamer & Hardware Simulator
Simulates Tyrant-AQ AUV dynamics, 4 Water Quality sensors, 6 Thrusters PWM, EKF Observer, and EA-DSRA intervals.
"""
import socket
import time
import math
import random
import threading


class MockTeensyStreamer:
    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.running = True

        # State Variables
        self.depth = 0.5
        self.target_depth = 1.5
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 45.0
        self.target_yaw = 45.0

        self.battery_v = 24.6
        self.soc_kalman = 92.0
        self.current_a = 2.8

        self.temp = 27.2
        self.ph = 7.45
        self.do_val = 6.20
        self.cond = 320.0

        self.tbm_temp = 3.0
        self.tbm_ph = 5.0
        self.tbm_do = 2.0
        self.tbm_cond = 4.0

        self.mode = "LMPC_AUTO"
        self.is_armed = True

    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(2)
        print(f"[SIMULATOR] Mock Teensy TCP Server listening on {self.host}:{self.port}...")

        while self.running:
            try:
                client_sock, addr = server_sock.accept()
                print(f"[SIMULATOR] GCS Connected from {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True)
                client_thread.start()
            except Exception as e:
                print(f"[SIMULATOR] Server error: {e}")
                break

    def handle_client(self, sock: socket.socket):
        sock.settimeout(0.1)
        step = 0

        rx_thread = threading.Thread(target=self.rx_loop, args=(sock,), daemon=True)
        rx_thread.start()

        while self.running:
            try:
                step += 1
                t_now = int(time.time() * 1000)

                # Simulate Dynamics (Depth smoothly approaching target)
                depth_err = self.target_depth - self.depth
                self.depth += depth_err * 0.05 + random.uniform(-0.01, 0.01)
                self.roll = 2.0 * math.sin(step * 0.05) + random.uniform(-0.3, 0.3)
                self.pitch = 3.0 * math.cos(step * 0.04) + random.uniform(-0.3, 0.3)
                self.yaw = (self.yaw + 0.2) % 360.0

                # Simulate Water Quality with Depth Stratification
                # Higher depth -> slightly lower temp, lower DO
                self.temp = 27.5 - 0.4 * self.depth + random.uniform(-0.02, 0.02)
                self.ph = 7.50 - 0.1 * self.depth + random.uniform(-0.02, 0.02)
                self.do_val = max(1.5, 6.8 - 0.8 * self.depth + random.uniform(-0.05, 0.05))
                self.cond = 310.0 + 15.0 * self.depth + random.uniform(-1.0, 1.0)

                # Simulate Power & Kalman Filtered Battery
                self.battery_v = max(19.8, self.battery_v - 0.0002)
                raw_v = self.battery_v + random.uniform(-0.15, 0.15)  # Motor noise
                self.soc_kalman = ((self.battery_v - 19.8) / (25.2 - 19.8)) * 100.0
                self.current_a = 2.5 + 1.2 * abs(depth_err) + random.uniform(-0.2, 0.2)

                # 6 Thrusters PWM Simulation
                base_vert = int(1500 + depth_err * 120)
                pwm5 = max(1100, min(1900, base_vert))
                pwm6 = max(1100, min(1900, base_vert + random.randint(-5, 5)))
                pwm1 = 1500 + random.randint(-40, 40)
                pwm2 = 1500 + random.randint(-40, 40)
                pwm3 = 1500 + random.randint(-40, 40)
                pwm4 = 1500 + random.randint(-40, 40)

                # EKF Current Disturbance (N)
                disturb_surge = 0.45 * math.sin(step * 0.02)
                disturb_sway = 0.30 * math.cos(step * 0.03)
                disturb_heave = 0.15

                # Construct Extended RT Line (32 Fields)
                # RT,ts,temp,ph,do,batt,curr,depth,cond,roll,pitch,yaw,pwm1..6,tbm_t/ph/do/c,raw_t/ph/do/c,press,soc,wcet,d_x,d_y,d_z
                packet = (
                    f"RT,{t_now},"
                    f"{self.temp:.2f},{self.ph:.2f},{self.do_val:.2f},{raw_v:.2f},{self.current_a:.2f},{self.depth:.2f},{self.cond:.1f},"
                    f"{self.roll:.1f},{self.pitch:.1f},{self.yaw:.1f},"
                    f"{pwm1},{pwm2},{pwm3},{pwm4},{pwm5},{pwm6},"
                    f"{self.tbm_temp:.1f},{self.tbm_ph:.1f},{self.tbm_do:.1f},{self.tbm_cond:.1f},"
                    f"{self.temp:.2f},{self.ph:.2f},{self.do_val:.2f},{self.cond:.1f},{1013.25 + self.depth*100:.1f},"
                    f"{self.soc_kalman:.1f},11.8,"
                    f"{disturb_surge:.2f},{disturb_sway:.2f},{disturb_heave:.2f}\n"
                )

                sock.sendall(packet.encode("utf-8"))
                time.sleep(0.1)  # 10 Hz telemetry loop

            except (socket.error, BrokenPipeError):
                print("[SIMULATOR] GCS Disconnected.")
                break
            except Exception as e:
                print(f"[SIMULATOR] Tx Loop Exception: {e}")
                break

    def rx_loop(self, sock: socket.socket):
        buf = ""
        while self.running:
            try:
                data = sock.recv(1024).decode("utf-8", errors="ignore")
                if not data:
                    break
                buf += data
                while "\n" in buf:
                    cmd, buf = buf.split("\n", 1)
                    cmd = cmd.strip()
                    if not cmd:
                        continue
                    print(f"[SIMULATOR RX] Received Command: {cmd}")
                    self.process_command(sock, cmd)
            except socket.timeout:
                pass
            except Exception:
                break

    def process_command(self, sock: socket.socket, cmd: str):
        parts = cmd.split(",")
        header = parts[0].upper()

        if header == "HELLO":
            sock.sendall(b"HELLO_ACK,TYRANT_AQ_V1.0\n")
        elif header == "SETPOINT":
            if len(parts) >= 2:
                try:
                    self.target_depth = float(parts[1])
                    print(f"[SIMULATOR] New Target Depth Set: {self.target_depth:.2f} m")
                except ValueError:
                    pass
        elif header == "MODE":
            self.mode = parts[1] if len(parts) > 1 else "MANUAL"
            sock.sendall(f"MODE_ACK,{self.mode}\n".encode())
        elif header == "ARM":
            self.is_armed = True
            sock.sendall(b"ARM_ACK,OK\n")
        elif header == "DISARM":
            self.is_armed = False
            sock.sendall(b"DISARM_ACK,OK\n")
        elif header == "LMPC_CONTROL":
            state = parts[1] if len(parts) > 1 else "OFF"
            self.mode = "LMPC_AUTO" if state == "ON" else "MANUAL"
            sock.sendall(f"LMPC_ACK,{state}\n".encode())
            print(f"[SIMULATOR] LMPC Control set to: {state}")
        elif header == "LMPC_PARAM":
            sock.sendall(b"LMPC_PARAM_ACK,OK\n")
            print(f"[SIMULATOR] Updated LMPC parameters: {cmd}")
        elif header == "EMERGENCY_KILL":
            self.is_armed = False
            sock.sendall(b"EMERGENCY_ACK,POWER_CUT_CONFIRMED\n")


if __name__ == "__main__":
    sim = MockTeensyStreamer(host="127.0.0.1", port=9000)
    sim.start()
