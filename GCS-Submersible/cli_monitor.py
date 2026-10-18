# -*- coding: utf-8 -*-
"""
Standalone Headless Telemetry Monitor & CLI for Submersible.
Runs directly in terminal with ZERO GUI / PyQt5 dependencies.
Ideal for Linux, WSL2, ROS2 debugging, or rapid hardware link testing with Teensy 4.1 & ESP32.
"""
import sys
import time
from core.gcs_service import GcsService

def print_banner():
    print("=" * 65)
    print("  TYRANT-AQ AUV - HEADLESS COMMAND & TELEMETRY MONITOR")
    print("  Pure Python Core - Standalone Testing Engine")
    print("=" * 65)
    print("Commands:")
    print("  mode <real|sim>   : Switch operating mode")
    print("  tcp <ip> <port>   : Connect Ethernet TCP (e.g. tcp 192.168.1.170 9000)")
    print("  serial <port>     : Connect USB Serial (e.g. serial COM3)")
    print("  disconnect        : Disconnect hardware")
    print("  sp <depth>        : Set target depth in meters (e.g. sp 1.5)")
    print("  arm / disarm      : Arm or Disarm thrusters")
    print("  kill              : Emergency stop all thrusters")
    print("  rec <name>        : Start CSV recording")
    print("  stoprec           : Stop CSV recording")
    print("  q / quit          : Exit CLI")
    print("=" * 65)


def on_telemetry(data: dict):
    depth = data.get("depth", 0.0)
    target_d = data.get("target_depth", 0.0)
    ph = data.get("ph", 0.0)
    do_val = data.get("do", 0.0)
    temp = data.get("temp", 0.0)
    batt = data.get("battery_v", 0.0)
    soc = data.get("soc_kalman", data.get("soc", 100.0))
    curr = data.get("current_a", 0.0)
    pwms = [data.get(f"pwm{i}", 1500) for i in range(1, 7)]

    # Print single line live summary
    sys.stdout.write(
        f"\r[TELEMETRY] Z: {depth:4.2f}m (SP:{target_d:4.2f}m) | pH: {ph:4.2f} | DO: {do_val:4.2f}mg/L | "
        f"T: {temp:4.1f}C | Batt: {batt:4.1f}V ({soc:3.0f}%) | I: {curr:4.2f}A | PWM: {pwms[:3]}"
    )
    sys.stdout.flush()

def on_log(msg: str):
    print(f"\n{msg}")


def on_connection(connected: bool, msg: str):
    status = "CONNECTED" if connected else "DISCONNECTED"
    print(f"\n[LINK {status}] {msg}")


def on_alert(level: str, key: str, desc: str):
    print(f"\n[ALERT - {level}] {key}: {desc}")


def main():
    print_banner()
    service = GcsService()

    # Wire pure Python event callbacks
    service.telemetry_received.connect(on_telemetry)
    service.log_emitted.connect(on_log)
    service.connection_changed.connect(on_connection)
    service.alert_triggered.connect(on_alert)

    # Default to SIMULATION mode for immediate testing
    service.set_operating_mode("SIMULATION")

    try:
        while True:
            cmd = input("\n>> ").strip()
            if not cmd:
                continue

            parts = cmd.split()
            c = parts[0].lower()

            if c in ("q", "quit", "exit"):
                break
            elif c == "mode":
                if len(parts) > 1:
                    m = "SIMULATION" if parts[1].lower().startswith("sim") else "REAL"
                    service.set_operating_mode(m)
                else:
                    print("Usage: mode <real|sim>")
            elif c == "tcp":
                ip = parts[1] if len(parts) > 1 else "192.168.1.170"
                port = int(parts[2]) if len(parts) > 2 else 9000
                service.set_operating_mode("REAL")
                service.start_connection(conn_type="TCP", ip=ip, port=port)
            elif c == "serial":
                port = parts[1] if len(parts) > 1 else "COM3"
                baud = int(parts[2]) if len(parts) > 2 else 115200
                service.set_operating_mode("REAL")
                service.start_connection(conn_type="SERIAL", serial_port=port, baud=baud)
            elif c == "disconnect":
                service.stop_connection()
            elif c == "sp":
                if len(parts) > 1:
                    try:
                        d = float(parts[1])
                        service.set_depth_setpoint(d)
                        print(f"Setpoint depth dikirim: {d:.2f} m")
                    except ValueError:
                        print("Error: depth harus angka desimal")
                else:
                    print("Usage: sp <depth_in_meters>")
            elif c == "arm":
                service.arm(True)
                print("Command ARM dikirim.")
            elif c == "disarm":
                service.arm(False)
                print("Command DISARM dikirim.")
            elif c == "kill":
                service.emergency_kill()
                print("Command EMERGENCY KILL dikirim!")
            elif c == "rec":
                name = parts[1] if len(parts) > 1 else "cli_session"
                fp = service.start_recording(mission_name=name)
                print(f"Perekaman dimulai: {fp}")
            elif c == "stoprec":
                res = service.stop_recording()
                print(f"Perekaman dihentikan: {res['rows']} baris tersimpan.")
            elif c == "help":
                print_banner()
            else:
                # Raw command passthrough
                service.send_command(cmd)

    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
    finally:
        service.shutdown()
        print("GcsService terminated cleanly.")


if __name__ == "__main__":
    main()
