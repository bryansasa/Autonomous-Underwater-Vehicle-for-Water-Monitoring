#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash
source "${TYRANT_SETUP:-/ws/install/setup.bash}"

deployment_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$deployment_dir/run_companion.py" "$@"
