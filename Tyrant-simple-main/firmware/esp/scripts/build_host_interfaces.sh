#!/usr/bin/env bash
set -eo pipefail
esp_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="$(cd -- "$esp_root/../.." && pwd)"
source /opt/ros/humble/setup.bash
cd "$repo_root/ros2_ws"
exec colcon build --packages-select tyrant_payload_interfaces --symlink-install
