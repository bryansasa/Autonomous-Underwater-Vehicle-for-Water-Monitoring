"""Lifecycle checks with fake ROS children, without DDS or hardware."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


LAUNCHER = Path(__file__).with_name('run_companion.py')
FAKE_ROS = '''#!/usr/bin/env python3
import os, pathlib, signal, sys, time
root = pathlib.Path(os.environ['FAKE_ROOT'])
role = sys.argv[1]
def stop(*args):
    (root / (role + '.stopped')).touch()
    sys.exit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
(root / (role + '.started')).write_text(' '.join(sys.argv))
while True:
    if role == 'run' and (root / 'fail').exists():
        sys.exit(7)
    time.sleep(0.05)
'''


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        executable = self.root / 'ros2'
        executable.write_text(FAKE_ROS)
        executable.chmod(0o755)
        self.device = self.root / 'serial'

    def start(self, connected=True, threshold=1):
        if connected:
            self.device.touch()
        self.child = subprocess.Popen([
            sys.executable, str(LAUNCHER), '--serial-device', str(self.device),
            '--bag-dir', str(self.root / 'bags'), '--min-free-mib', str(threshold),
        ], env=dict(os.environ, PATH=str(self.root) + ':' + os.environ['PATH'],
                    FAKE_ROOT=str(self.root)), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.cleanup_child)

    def cleanup_child(self):
        if self.child.poll() is None:
            self.child.terminate()
        self.child.communicate(timeout=30)

    def wait_started(self):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if all((self.root / (role + '.started')).exists() for role in ('run', 'bag')):
                return
            time.sleep(0.05)
        self.fail('Children did not start')

    def test_shutdown_signals_both_children(self):
        self.start()
        self.wait_started()
        self.child.send_signal(signal.SIGTERM)
        self.assertEqual(self.child.wait(timeout=5), 0)
        for role in ('run', 'bag'):
            self.assertTrue((self.root / (role + '.stopped')).exists())

    def test_agent_failure_stops_recorder(self):
        self.start()
        self.wait_started()
        (self.root / 'fail').touch()
        self.assertEqual(self.child.wait(timeout=5), 1)
        self.assertTrue((self.root / 'bag.stopped').exists())

    def test_disconnect_stops_both_children(self):
        self.start()
        self.wait_started()
        self.device.unlink()
        self.assertEqual(self.child.wait(timeout=5), 1)
        for role in ('run', 'bag'):
            self.assertTrue((self.root / (role + '.stopped')).exists())

    def test_low_disk_prevents_start(self):
        self.start(threshold=10**12)
        self.assertEqual(self.child.wait(timeout=5), 1)
        self.assertFalse((self.root / 'run.started').exists())


if __name__ == '__main__':
    unittest.main()
