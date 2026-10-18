#!/usr/bin/env python3
"""Supervise the serial agent and recorder; never grant control authority."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import uuid


TOPICS = (
    '/tyrant/simple_state', '/tyrant/sensors/imu', '/tyrant/sensors/pressure',
    '/tyrant/system/health', '/tyrant/mode/status',
    '/tyrant/communication/diagnostics', '/tyrant/control/wrench_request',
    '/tyrant/control/thruster_command', '/tyrant/actuation/status',
    '/tyrant/mission/status', '/tyrant/emergency/status',
    '/tyrant/sysid/status', '/tyrant/sysid/sample',
)


def signal_child(child, signum):
    try:
        os.killpg(child.pid, signum)
    except ProcessLookupError:
        pass  # The process may exit between poll() and killpg().


def stop_children(children):
    # Give rosbag SIGINT first so SQLite and metadata can be finalized.
    for child in reversed(children):
        if child.poll() is None:
            signal_child(child, signal.SIGINT)
    deadline = time.monotonic() + 20
    for child in reversed(children):
        try:
            child.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            signal_child(child, signal.SIGTERM)
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                signal_child(child, signal.SIGKILL)
                child.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial-device', default=os.environ.get(
        'TYRANT_SERIAL_DEVICE',
        '/host-dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00'))
    parser.add_argument('--bag-dir', default=os.environ.get('TYRANT_BAG_DIR', '/ws/bags'))
    parser.add_argument('--min-free-mib', type=int, default=512)
    args = parser.parse_args()
    if args.min_free_mib < 1:
        parser.error('--min-free-mib must be positive')

    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    children = []
    try:
        bag_root = Path(args.bag_dir)
        bag_root.mkdir(parents=True, exist_ok=True)
        print(f'Waiting for Teensy: {args.serial_device}', flush=True)
        while not Path(args.serial_device).exists():
            if stopping:
                return 0
            time.sleep(1)
        if stopping:
            return 0
        if shutil.disk_usage(bag_root).free < args.min_free_mib * 1024**2:
            raise RuntimeError('Not enough free storage for recording')

        session = datetime.now(timezone.utc).strftime('jetson_%Y%m%dT%H%M%SZ_')
        bag_path = bag_root / (session + uuid.uuid4().hex[:8])
        commands = (
            ['ros2', 'run', 'micro_ros_agent', 'micro_ros_agent', 'serial',
             '--dev', args.serial_device, '-v4'],
            ['ros2', 'bag', 'record', '-o', str(bag_path),
             '--max-bag-duration', '300', *TOPICS],
        )
        for command in commands:
            children.append(subprocess.Popen(command, start_new_session=True))
        print(f'Recording to {bag_path}; no automatic heartbeat or mode request', flush=True)
        while not stopping:
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(f'Child process {child.pid} exited ({child.returncode})')
            if not Path(args.serial_device).exists():
                raise RuntimeError('Teensy disconnected; restart will wait for its stable path')
            if shutil.disk_usage(bag_root).free < args.min_free_mib * 1024**2:
                raise RuntimeError('Free storage below recording threshold')
            time.sleep(1)
        return 0
    except (OSError, RuntimeError) as error:
        print(f'Companion stopped: {error}', flush=True)
        return 1
    finally:
        stop_children(children)


if __name__ == '__main__':
    raise SystemExit(main())
