#!/usr/bin/env python3
"""Keep the host and per-device agents running; never start a mission."""

import os
from pathlib import Path
import signal
import subprocess
import time

from ament_index_python.packages import get_package_prefix, get_package_share_directory


def executable(package, name):
    path = Path(get_package_prefix(package)) / 'lib' / package / name
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f'Executable unavailable: {path}')
    return str(path)


def start(name, command):
    child = subprocess.Popen(command, start_new_session=True)
    print(f'Started {name}: PID {child.pid}', flush=True)
    return child


def stop(child):
    if child is None:
        return
    # Signal the group even if its leader has exited, to collect remaining children.
    for signum, timeout in ((signal.SIGINT, 12), (signal.SIGTERM, 3), (signal.SIGKILL, 1)):
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            break
        try:
            child.wait(timeout=timeout)
            break
        except subprocess.TimeoutExpired:
            continue
    child.wait()


def flag(name, default):
    value = os.environ.get(name, default).lower()
    if value not in ('true', 'false'):
        raise ValueError(f'{name} must be true or false')
    return value == 'true'


def stop_host(host):
    if host is not None and host.poll() is None:
        # Keep the host spinning long enough to send STOP/SAFE and serialized OFF ACKs.
        try:
            result = subprocess.run(['ros2', 'service', 'call', '/tyrant/host/mission/stop',
                'std_srvs/srv/Trigger', '{}'], timeout=6, check=False,
                start_new_session=True)
            if result.returncode == 0:
                time.sleep(2.5)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f'Stop service unavailable during shutdown: {error}', flush=True)
    stop(host)


def main():
    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    host = plant = None
    agents = {}
    try:
        simulated = flag('TYRANT_TEENSY_SIMULATED', 'true')
        with_plant = flag('TYRANT_HIL_PLANT', 'false')
        if with_plant and not simulated:
            raise ValueError('HIL plant requires TYRANT_TEENSY_SIMULATED=true')
        payload = os.environ.get('TYRANT_PAYLOAD_NAMESPACE', '/tyrant/payload_sim')
        plan = os.environ.get('TYRANT_PLAN', str(Path(get_package_share_directory(
            'tyrant_mission_host')) / 'config' / 'two_depth_hil_sampling_020m.yaml'))
        if not Path(plan).is_file():
            raise RuntimeError(f'Mission plan unavailable: {plan}')
        agent_executable = executable('micro_ros_agent', 'micro_ros_agent')
        if with_plant:
            plant = start('HIL plant', [executable('tyrant_sim', 'tyrant_plant_sim'),
                '--ros-args', '--params-file', str(Path(get_package_share_directory(
                    'tyrant_sim')) / 'config' / 'reduced_plant.yaml')])
        host = start('mission host (IDLE)', [executable('tyrant_mission_host', 'mission_host'),
            '--ros-args', '-p', 'plan:=' + plan, '-p', 'payload_namespace:=' + payload,
            '-p', 'teensy_simulated:=' + str(simulated).lower(),
            '-p', 'publish_heartbeats:=true', '-p', 'output_dir:=' + os.environ.get(
                'TYRANT_OUTPUT_DIR', '/mission_ws/bags/missions')])
        for name, variable, default in (
                ('Teensy', 'TYRANT_TEENSY_PORT', '/host-dev/tyrant-teensy'),
                ('ESP', 'TYRANT_ESP_PORT', '/host-dev/tyrant-esp')):
            agents[name] = dict(path=os.environ.get(variable, default), child=None,
                                retry_at=0.0, waiting=False)
        print('Automatic dual heartbeat enabled. Mission remains IDLE until explicit start.', flush=True)
        while not stopping:
            for name, child in (('mission host', host), ('HIL plant', plant)):
                if child is not None and child.poll() is not None:
                    raise RuntimeError(f'{name} exited: {child.returncode}')
            for name, agent in agents.items():
                available = Path(agent['path']).exists()
                child = agent['child']
                if child is not None and (child.poll() is not None or not available):
                    print(f'{name} agent stopped or port disappeared; waiting to reconnect', flush=True)
                    stop(child)
                    agent['child'] = None
                    agent['retry_at'] = time.monotonic() + 2.0
                if not available:
                    if not agent['waiting']:
                        print(f'Waiting for {name}: {agent["path"]}', flush=True)
                    agent['waiting'] = True
                elif agent['child'] is None and time.monotonic() >= agent['retry_at']:
                    agent['waiting'] = False
                    agent['child'] = start(name + ' agent', [agent_executable, 'serial',
                        '--dev', agent['path'], '-b', '115200', '-v4'])
            time.sleep(0.5)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f'Mission companion stopped: {error}', flush=True)
        return 1
    finally:
        # Stop the host while agents are still available; finalize its active recording.
        stop_host(host)
        stop(plant)
        for agent in agents.values():
            stop(agent['child'])


if __name__ == '__main__':
    raise SystemExit(main())
