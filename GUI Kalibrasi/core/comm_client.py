# -*- coding: utf-8 -*-
"""
TCP/IP Communication Client for Teensy 4.1 Calibration Suite
Handles asynchronous socket communication, data parsing, and command transmission.
"""

import socket
import threading
import time
from PyQt5 import QtCore

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class CommClient(QtCore.QObject):
    telemetry_received = QtCore.pyqtSignal(dict)
    cal_response_received = QtCore.pyqtSignal(str, str)  # sensor, response
    mag_sample_received = QtCore.pyqtSignal(float, float, float)  # bx, by, bz
    raw_line_received = QtCore.pyqtSignal(str)
    connection_changed = QtCore.pyqtSignal(bool, str)  # is_connected, message
    log_message = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sock = None
        self.ser = None
        self.conn_type = "NONE"  # "TCP" or "SERIAL"
        self.is_connected = False
        self.host = "192.168.1.177"
        self.port = 9001
        self.serial_port = "COM6"
        self.serial_baud = 115200
        self._running = False
        self._rx_thread = None
        self._lock = threading.Lock()

    @staticmethod
    def get_available_ports() -> list:
        if not HAS_SERIAL:
            return []
        try:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            return sorted(ports)
        except Exception:
            return []

    def connect_to_serial(self, port_name: str, baudrate: int = 115200, timeout: float = 0.5):
        if self.is_connected:
            self.disconnect_from_host()

        if not HAS_SERIAL:
            self.connection_changed.emit(False, "pyserial belum terpasang.")
            self.log_message.emit("ERROR: Library pyserial tidak ditemukan.")
            return

        self.serial_port = port_name
        self.serial_baud = baudrate
        self.log_message.emit(f"Membuka port serial {self.serial_port} pada {self.serial_baud} bps...")

        def _worker():
            try:
                s = serial.Serial(self.serial_port, self.serial_baud, timeout=timeout)
                # ESP32-S3 USB CDC requires DTR=True to activate endpoint and stream data to host
                try:
                    s.dtr = True
                    s.rts = True
                    time.sleep(0.05)
                except Exception:
                    pass

                with self._lock:
                    self.ser = s
                    self.conn_type = "SERIAL"
                    self.is_connected = True
                    self._running = True

                self.connection_changed.emit(True, f"Terhubung ke {self.serial_port} ({self.serial_baud} bps)")
                self.log_message.emit(f"Berhasil terhubung ke port serial {self.serial_port}")

                self._start_serial_rx_loop()
            except Exception as e:
                self.is_connected = False
                self.ser = None
                self.conn_type = "NONE"
                self.connection_changed.emit(False, f"Gagal buka port serial: {e}")
                self.log_message.emit(f"ERROR: Gagal membuka {self.serial_port} — {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def connect_to_host(self, host: str, port: int, timeout: float = 3.0):
        if self.is_connected:
            self.disconnect_from_host()

        self.host = host
        self.port = port
        self.log_message.emit(f"Menghubungkan ke {self.host}:{self.port}...")

        def _worker():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((self.host, self.port))
                s.settimeout(0.5)

                with self._lock:
                    self.sock = s
                    self.conn_type = "TCP"
                    self.is_connected = True
                    self._running = True

                self.connection_changed.emit(True, f"Terhubung ke {self.host}:{self.port}")
                self.log_message.emit(f"Berhasil terhubung ke {self.host}:{self.port}")

                # Send initial handshake / newline
                try:
                    s.sendall(b"\n")
                except Exception:
                    pass

                self._start_tcp_rx_loop()
            except Exception as e:
                self.is_connected = False
                self.sock = None
                self.conn_type = "NONE"
                self.connection_changed.emit(False, f"Koneksi gagal: {e}")
                self.log_message.emit(f"ERROR: Gagal terhubung — {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def disconnect_from_host(self):
        self._running = False
        with self._lock:
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None

            self.conn_type = "NONE"
            self.is_connected = False

        self.connection_changed.emit(False, "Terputus.")
        self.log_message.emit("Koneksi ditutup.")

    def send_command(self, cmd: str) -> bool:
        if not self.is_connected:
            self.log_message.emit(f"ERROR TX: Tidak terhubung. Perintah dibatalkan: {cmd}")
            return False

        try:
            full_cmd = cmd.strip() + "\n"
            with self._lock:
                if self.conn_type == "TCP" and self.sock:
                    self.sock.sendall(full_cmd.encode("utf-8"))
                elif self.conn_type == "SERIAL" and self.ser:
                    self.ser.write(full_cmd.encode("utf-8"))
                    self.ser.flush()
            self.log_message.emit(f"TX -> {cmd.strip()}")
            return True
        except Exception as e:
            self.log_message.emit(f"ERROR TX: Pengiriman gagal — {e}")
            self.disconnect_from_host()
            return False

    def _start_tcp_rx_loop(self):
        buf = ""
        while self._running and self.sock:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    self.log_message.emit("Koneksi TCP ditutup oleh remote.")
                    break
                buf += chunk.decode("utf-8", errors="replace")

                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip("\r").strip()
                    if line:
                        self.raw_line_received.emit(line)
                        self._parse_line(line)
            except socket.timeout:
                continue
            except (OSError, socket.error):
                if self._running:
                    self.log_message.emit("Socket terputus / error.")
                break
            except Exception as e:
                self.log_message.emit(f"RX Exception: {e}")
                break

        if self.is_connected:
            self.disconnect_from_host()

    def _start_serial_rx_loop(self):
        buf = ""
        while self._running and self.ser:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buf += data.decode("utf-8", errors="replace")

                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip("\r").strip()
                        if line:
                            self.raw_line_received.emit(line)
                            self._parse_line(line)
                else:
                    time.sleep(0.01)
            except (OSError, serial.SerialException) as e:
                if self._running:
                    self.log_message.emit(f"Port serial error: {e}")
                break
            except Exception as e:
                self.log_message.emit(f"Serial RX Exception: {e}")
                break

        if self.is_connected:
            self.disconnect_from_host()

    def _parse_line(self, line: str):
        # Format 1: Realtime Telemetry -> CAL_RT,ts,ph,ec,do,temp[,roll,pitch,yaw,depth,press]
        if line.startswith("CAL_RT,"):
            self._parse_cal_rt(line)
        # Format 2: Calibration Response -> CAL_RESP,SENSOR,RESPONSE
        elif line.startswith("CAL_RESP,"):
            parts = line.split(",", 2)
            if len(parts) >= 3:
                sensor = parts[1].strip()
                resp = parts[2].strip()
                self.cal_response_received.emit(sensor, resp)
                self.log_message.emit(f"CAL_RESP [{sensor}]: {resp}")
        # Format 3: Raw Magnetometer Stream -> CAL_MAG_RAW,bx,by,bz
        elif line.startswith("CAL_MAG_RAW,"):
            parts = line.split(",")
            if len(parts) >= 4:
                try:
                    bx = float(parts[1])
                    by = float(parts[2])
                    bz = float(parts[3])
                    self.mag_sample_received.emit(bx, by, bz)
                except ValueError:
                    pass
        # Format 4: Fallback response check (*OK / ?CAL)
        elif line.startswith("*OK") or line.startswith("?CAL"):
            self.cal_response_received.emit("EC", line)
            self.log_message.emit(f"CAL_RESP [EC]: {line}")
        # Format 5: Fallback loose reading "[BACAAN EC]: <val>"
        elif "[BACAAN EC]:" in line or "EC:" in line:
            self.log_message.emit(f"RX <- {line}")
            try:
                import re
                m = re.search(r"[-+]?\d*\.?\d+", line.split("EC", 1)[-1])
                if m:
                    ec_val = float(m.group(0))
                    data = {
                        "ts": time.time() * 1000,
                        "ph": 7.00,
                        "ec": ec_val,
                        "do": 6.50,
                        "temp": 25.0,
                        "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "depth": 0.0, "press": 1013.25
                    }
                    self.telemetry_received.emit(data)
            except Exception:
                pass
        else:
            self.log_message.emit(f"RX <- {line}")

    def _parse_cal_rt(self, line: str):
        try:
            parts = line.split(",")
            if len(parts) < 6:
                return

            # Pastikan nilai pH berupa angka valid, jika bukan (misal sisa respon '?CAL') lewati frame ini
            try:
                ph_val = float(parts[2])
            except (ValueError, TypeError):
                return

            def _to_float(val, default=0.0):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            # Dasar Kualitas Air (kompatibel WGG)
            data = {
                "ts": float(parts[1]) if parts[1].replace(".", "", 1).isdigit() else time.time(),
                "ph": ph_val,
                "ec": _to_float(parts[3]),
                "do": _to_float(parts[4]),
                "temp": _to_float(parts[5], 25.0),
                # Default orientasi & gerak jika paket extended tersedia
                "roll": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "depth": 0.0,
                "press": 1013.25
            }

            # Extended fields (Orientasi & Kedalaman Charisto)
            if len(parts) >= 11:
                data["roll"] = _to_float(parts[6])
                data["pitch"] = _to_float(parts[7])
                data["yaw"] = _to_float(parts[8])
                data["depth"] = _to_float(parts[9])
                data["press"] = _to_float(parts[10], 1013.25)

            self.telemetry_received.emit(data)
        except Exception as e:
            self.log_message.emit(f"Parse error [CAL_RT]: {e} on '{line}'")
