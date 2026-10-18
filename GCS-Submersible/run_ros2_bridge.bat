@echo off
title Tyrant-AQ - ROS 2 to GCS Bridge
echo ========================================================
echo Membuka ROS 2 to GCS Bridge (micro-ROS Adapter)
echo Mendengarkan koneksi GCS di port 9000
echo ========================================================
python gcs_ros2_bridge.py %*
pause
