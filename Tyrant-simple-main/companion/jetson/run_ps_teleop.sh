#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

source /opt/ros/humble/setup.bash
source "${REPO_ROOT}/ros2_ws/install/setup.bash"

exec ros2 launch tyrant_teleop ps_teleop.launch.py
