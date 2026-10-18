#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
source /mission_ws/install/setup.bash
exec python3 /deployment/run_mission_companion.py
