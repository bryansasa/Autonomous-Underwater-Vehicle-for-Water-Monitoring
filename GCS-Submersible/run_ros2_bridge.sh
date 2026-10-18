#!/usr/bin/env bash
echo "========================================================"
echo "Membuka ROS 2 to GCS Bridge (micro-ROS Adapter)"
echo "Pastikan micro-ROS Agent sudah berjalan!"
echo "========================================================"
# Source ROS 2 jika belum disource
if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
elif [ -f "/opt/ros/iron/setup.bash" ]; then
    source /opt/ros/iron/setup.bash
fi

# Source tyrant_payload_interfaces jika telah di-build
if [ -f "../ros2_ws/install/setup.bash" ]; then
    source ../ros2_ws/install/setup.bash
elif [ -f "./ros2_ws/install/setup.bash" ]; then
    source ./ros2_ws/install/setup.bash
elif [ -f "$HOME/tyrant-simple/firmware/esp/host_ws/install/setup.bash" ]; then
    source "$HOME/tyrant-simple/firmware/esp/host_ws/install/setup.bash"
fi

python3 gcs_ros2_bridge.py "$@"

