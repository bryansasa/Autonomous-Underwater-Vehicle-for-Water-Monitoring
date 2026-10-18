#!/usr/bin/env bash
# ========================================================
# Simulasi Penuh Gazebo ROV + EA-DSRA Waduk Saguling
# ========================================================
set -e

echo "========================================================"
echo "  Meluncurkan Simulasi Gazebo ROV Tyrant-AQ & EA-DSRA"
echo "  Waduk Saguling - Telkom University"
echo "========================================================"

cd "$(dirname "$0")/ros2_ws"

# Source ROS 2 jika belum
if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
elif [ -f "/opt/ros/iron/setup.bash" ]; then
    source /opt/ros/iron/setup.bash
fi

# Build packages jika belum terpasang
if [ ! -d "install/tyrant_gazebo_sim" ]; then
    echo "[INFO] Melakukan build package tyrant_gazebo_sim & tyrant_payload_interfaces..."
    colcon build --symlink-install
fi

source install/setup.bash

echo "[INFO] Menjalankan Gazebo dan Subsistem EA-DSRA..."
ros2 launch tyrant_gazebo_sim simulasi_rov_gazebo.launch.py
