#!/usr/bin/env bash
# ========================================================
# Simulasi Standalone ROS 2 Subsistem EA-DSRA Waduk Saguling
# ========================================================
set -e

echo "========================================================"
echo "  Meluncurkan Server Kualitas Air & EA-DSRA (ROS 2 SITL)"
echo "  Waduk Saguling - Telkom University"
echo "========================================================"

cd "$(dirname "$0")/ros2_ws"

if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
elif [ -f "/opt/ros/iron/setup.bash" ]; then
    source /opt/ros/iron/setup.bash
fi

if [ ! -d "install/tyrant_gazebo_sim" ]; then
    echo "[INFO] Melakukan build package..."
    colcon build --symlink-install
fi

source install/setup.bash

echo "[INFO] Menjalankan server kualitas air dan EA-DSRA..."
ros2 launch tyrant_gazebo_sim simulasi_rov_standalone.launch.py
