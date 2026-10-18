# -*- coding: utf-8 -*-
"""
Launch file: Simulasi Penuh ROV Tyrant-AQ di Gazebo + Medan Air Saguling + Subsistem EA-DSRA
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('tyrant_gazebo_sim')
    world_path = os.path.join(pkg_dir, 'worlds', 'saguling_reservoir.sdf')
    model_path = os.path.join(pkg_dir, 'models', 'tyrant_rov', 'model.sdf')

    # 1. Jalankan Gazebo Sim (Ignition) dengan World Waduk Saguling
    # Jika gz sim terinstall
    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_path],
        output='screen'
    )

    # 2. Spawn Model ROV Tyrant-AQ ke dalam World
    gz_spawn = ExecuteProcess(
        cmd=['gz', 'service', '-s', '/world/saguling_reservoir/create',
             '--reqtype', 'gz.msgs.EntityFactory',
             '--reptype', 'gz.msgs.Boolean',
             '--timeout', '1000',
             '--req', f'sdf_filename: "{model_path}", name: "tyrant_rov"'],
        output='screen'
    )

    # 3. Jembatan Komunikasi ROS 2 <-> Gazebo Sim (ros_gz_bridge)
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/model/tyrant_rov/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/tyrant_rov/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image',
        ],
        output='screen'
    )

    # 4. Node Server Medan Air Waduk Saguling (Mengonversi posisi Z Gazebo -> Kualitas Air)
    saguling_field_server = Node(
        package='tyrant_gazebo_sim',
        executable='saguling_field_server',
        name='saguling_field_server',
        output='screen'
    )

    # 5. Node Subsistem EA-DSRA (Manajemen Daya Adaptif & Safety Override)
    ea_dsra_node = Node(
        package='tyrant_gazebo_sim',
        executable='ea_dsra_node',
        name='ea_dsra_node',
        output='screen'
    )

    return LaunchDescription([
        gz_sim,
        gz_spawn,
        ros_gz_bridge,
        saguling_field_server,
        ea_dsra_node
    ])
