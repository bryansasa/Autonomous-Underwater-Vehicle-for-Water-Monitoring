# -*- coding: utf-8 -*-
"""
Pure Python Communication Engine for Submersible GCS.
Handles Ethernet TCP/UDP, USB Serial, and Internal Simulation modes.
Completely decoupled from PyQt5 and any GUI framework.
Can be imported directly by ROS2 nodes, CLI utilities, and test scripts.
"""
import socket
import time
import threading
from typing import Optional, Dict, Any
import serial

from core.telemetry_parser import TelemetryParser
from core.internal_simulator import InternalSimulator
from core.event_hook import EventHook


class CommEngine:
    """
    Standalone vehicle communication engine managing physical link and simulation.
    Thread-safe, event-driven, zero external GUI dependencies.
    """
    def __init__(self):
        self.running = False
        self.operating_mode = "REAL"  # "REAL" or "SIMULATION"

        # Connection parameters
        self.conn_type = "TCP"  # "TCP", "UDP", "SERIAL"
        self.target_ip = "192.168.1.170"
        self.target_port = 9000
        self.serial_port = "COM3"
        self.serial_baud = 115200

        # Physical link objects
        self.sock: Optional[socket.socket] = None
        self.ser: Optional[serial.Serial] = None
        self._connected = False

        # Threading & queues
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._send_queue = []

        # Internal simulator engine
        self.simulator = InternalSimulator()

        # Pure-Python Event Hooks
        self.telemetry_received = EventHook()      # (data: dict)
        self.raw_received = EventHook()            # (raw_str: str)
        self.connection_changed = EventHook()      # (is_connected: bool, message: str)
        self.log_emitted = EventHook()            # (log_message: str)
        self.error_occurred = EventHook()          # (error_message: str)
        self.operating_mode_changed = EventHook()  # (mode: str)

        # Connect simulator hooks
        self.simulator.telemetry_generated.connect(self._on_simulator_telemetry)
        self.simulator.raw_packet_generated.connect(self._on_simulator_raw)
        self.simulator.log_emitted.connect(self._on_simulator_log)

    def set_config(self, conn_type="TCP", ip="192.168.1.170", port=9000, serial_port="COM3", baud=115200):
        """Set connection parameters."""
        self.conn_type = conn_type.upper()
        self.target_ip = ip
        self.target_port = int(port)
        self.serial_port = serial_port
        self.serial_baud = int(baud)

    def set_operating_mode(self, mode: str):
        """Switch between REAL hardware and SIMULATION dummy engine."""
        mode = mode.upper()
        if mode not in ("REAL", "SIMULATION"):
            return

        self.operating_mode = mode
        if mode == "SIMULATION":
            self.stop()
            self.simulator.start()
            self._connected = True
            self.connection_changed.emit(True, "Mode Simulasi Aktif (Dummy Internal)")
            self.log_emitted.emit("[SYSTEM] Beralih ke Mode SIMULASI (Dummy).")
        else:
            self.simulator.stop()
            self._connected = False
            self.connection_changed.emit(False, "Disconnected (Hardware Mode)")
            self.log_emitted.emit("[SYSTEM] Beralih ke Mode REAL HARDWARE.")

        self.operating_mode_changed.emit(mode)

    def start(self, conn_type: Optional[str] = None, ip: Optional[str] = None, port: Optional[int] = None,
              serial_port: Optional[str] = None, baud: Optional[int] = None):
        """Start communication worker thread."""
        if conn_type or ip or port or serial_port or baud:
            self.set_config(
                conn_type=conn_type or self.conn_type,
                ip=ip or self.target_ip,
                port=port or self.target_port,
                serial_port=serial_port or self.serial_port,
                baud=baud or self.serial_baud
            )

        if self.operating_mode == "SIMULATION":
            self.simulator.start()
            self._connected = True
            self.connection_changed.emit(True, "Mode Simulasi Aktif (Dummy Internal)")
            return

        if self.running:
            self.stop()

        self.running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="CommEngineWorker")
        self._thread.start()

    def stop(self):
        """Stop worker and close all sockets/serial ports."""
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        self._close_all()
        self._connected = False
        self.connection_changed.emit(False, "Disconnected")

    def is_connected(self) -> bool:
        if self.operating_mode == "SIMULATION":
            return self.simulator.running
        return self._connected

    def send_command(self, cmd: str):
        """Queue a command string to be transmitted."""
        if not cmd.endswith("\n"):
            cmd += "\n"

        if self.operating_mode == "SIMULATION":
            self.simulator.process_command(cmd)
            self.log_emitted.emit(f">>> [SIM TX] {cmd.strip()}")
            return

        with self._lock:
            self._send_queue.append(cmd)

    def _worker_loop(self):
        """Background thread communication loop."""
        buffer = ""
        while self.running:
            if not self._connected:
                self._try_connect()
                if not self._connected:
                    time.sleep(1.0)
                    continue

            # Process TX queue
            self._process_send_queue()

            # Process RX
            try:
                if self.conn_type == "TCP" and self.sock:
                    try:
                        data = self.sock.recv(4096)
                        if data:
                            buffer += data.decode("utf-8", errors="ignore")
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if line:
                                    self._handle_incoming_line(line)
                        else:
                            self.log_emitted.emit("[NET] Koneksi TCP terputus oleh remote server.")
                            self._close_all()
                            self._connected = False
                            self.connection_changed.emit(False, "TCP Remote Closed")
                    except BlockingIOError:
                        pass
                    except socket.timeout:
                        pass

                elif self.conn_type == "UDP" and self.sock:
                    try:
                        data, addr = self.sock.recvfrom(4096)
                        if data:
                            buffer += data.decode("utf-8", errors="ignore")
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if line:
                                    self._handle_incoming_line(line)
                    except BlockingIOError:
                        pass

                elif self.conn_type == "SERIAL" and self.ser and self.ser.is_open:
                    if self.ser.in_waiting > 0:
                        raw = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="ignore")
                        buffer += raw
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if line:
                                self._handle_incoming_line(line)

            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"RX Error: {e}")
                    self.log_emitted.emit(f"[COMM ERROR] {e}")
                    self._close_all()
                    self._connected = False
                    self.connection_changed.emit(False, f"Error: {e}")

            time.sleep(0.01)

    def _try_connect(self):
        self._close_all()
        try:
            if self.conn_type == "TCP":
                self.log_emitted.emit(f"[NET] Menghubungkan TCP ke {self.target_ip}:{self.target_port}...")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.5)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.connect((self.target_ip, self.target_port))
                s.sendall(b"HELLO\n")
                s.setblocking(False)
                self.sock = s
                self._connected = True
                self.connection_changed.emit(True, f"Connected TCP {self.target_ip}:{self.target_port}")
                self.log_emitted.emit(f"[NET] Terhubung ke Ethernet: {self.target_ip}:{self.target_port}")

            elif self.conn_type == "UDP":
                self.log_emitted.emit(f"[NET] Membuka port UDP {self.target_port}...")
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.1)
                s.bind(("", self.target_port))
                s.setblocking(False)
                self.sock = s
                self._connected = True
                self.connection_changed.emit(True, f"Listening UDP Port {self.target_port}")
                self.log_emitted.emit(f"[NET] UDP siap pada port {self.target_port}")

            elif self.conn_type == "SERIAL":
                self.log_emitted.emit(f"[SERIAL] Membuka port {self.serial_port} @ {self.serial_baud} baud...")
                self.ser = serial.Serial(self.serial_port, self.serial_baud, timeout=0.1)
                self._connected = True
                self.connection_changed.emit(True, f"Connected Serial {self.serial_port}")
                self.log_emitted.emit(f"[SERIAL] Port {self.serial_port} berhasil dibuka.")
                self.send_command("GETCONFIG\n")

        except Exception as e:
            self._connected = False
            self.connection_changed.emit(False, f"Gagal Konek: {e}")

    def _close_all(self):
        with self._lock:
            if self.sock:
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

    def _process_send_queue(self):
        with self._lock:
            while self._send_queue:
                cmd = self._send_queue.pop(0)
                try:
                    cmd_bytes = cmd.encode("utf-8")
                    if self.conn_type == "TCP" and self.sock:
                        self.sock.sendall(cmd_bytes)
                    elif self.conn_type == "UDP" and self.sock:
                        self.sock.sendto(cmd_bytes, (self.target_ip, self.target_port))
                    elif self.conn_type == "SERIAL" and self.ser and self.ser.is_open:
                        self.ser.write(cmd_bytes)
                except Exception as e:
                    self.log_emitted.emit(f"[TX ERROR] Gagal mengirim '{cmd.strip()}': {e}")

    def _handle_incoming_line(self, line: str):
        self.raw_received.emit(line)
        if line.startswith("RT,"):
            parsed = TelemetryParser.parse_rt_line(line)
            if parsed:
                self.telemetry_received.emit(parsed)
        elif line.startswith("CONFIG,") or line.startswith("PID_ACK,") or line.startswith("SAMPLE_ACK,"):
            self.log_emitted.emit(f"[ACK] {line}")

    def _on_simulator_telemetry(self, data: Dict[str, Any]):
        if self.operating_mode == "SIMULATION":
            self.telemetry_received.emit(data)

    def _on_simulator_raw(self, raw_pkt: str):
        if self.operating_mode == "SIMULATION":
            self.raw_received.emit(raw_pkt)

    def _on_simulator_log(self, msg: str):
        self.log_emitted.emit(msg)
