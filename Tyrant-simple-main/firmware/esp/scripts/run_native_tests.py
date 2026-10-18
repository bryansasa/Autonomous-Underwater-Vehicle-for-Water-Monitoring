#!/usr/bin/env python3
"""Compile production payload logic with fake GPIO/I2C; no ROS workspace writes."""
import pathlib
import re
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--simulation', action='store_true')
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
build = root / '.native-test'
headers = build / 'include' / 'tyrant_payload_interfaces' / 'msg'
headers.mkdir(parents=True, exist_ok=True)
types = {'uint8': 'uint8_t', 'uint32': 'uint32_t', 'uint64': 'uint64_t',
         'float32': 'float', 'bool': 'bool'}
for msg in (root / 'extra_packages/tyrant_payload_interfaces/msg').glob('*.msg'):
    fields = []
    for raw in msg.read_text().splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line or '=' in line:
            continue
        kind, name = line.split()
        fields.append(f'    {types[kind]} {name};')
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', msg.stem).lower()
    struct_name = f'tyrant_payload_interfaces__msg__{msg.stem}'
    (headers / f'{snake}.h').write_text('#pragma once\n#include <stdint.h>\n'
        + f'struct {struct_name} {{\n' + '\n'.join(fields) + '\n};\n')
sources = ['connection_health', 'power_controller', 'payload_i2c', 'payload_monitor',
           'water_quality_lib', 'ea_dsra']
command = ['g++', '-std=c++14', '-Wall', '-Wextra', '-Werror', '-g',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-DPAYLOAD_NATIVE_TEST', '-I'+str(root/'test/native'),
           '-I'+str(build/'include'), '-I'+str(root/'include'),
           str(root/'test/native'/('test_simulation.cpp' if args.simulation else 'test_payload.cpp'))]
if args.simulation:
    sources = ['connection_health', 'power_controller', 'payload_simulation', 'ea_dsra']
    command += ['-DPAYLOAD_SIMULATION']
command += [str(root/'src'/f'{name}.cpp') for name in sources]
executable = build / ('test_simulation' if args.simulation else 'test_payload')
command += ['-o', str(executable)]
subprocess.run(command, check=True)
subprocess.run([str(executable)], check=True)
