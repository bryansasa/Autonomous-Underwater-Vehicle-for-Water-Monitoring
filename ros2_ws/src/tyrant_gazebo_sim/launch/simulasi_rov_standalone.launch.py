# -*- coding: utf-8 -*-
"""
Launch file: Simulasi Standalone Medan Air Saguling + Subsistem EA-DSRA
(Dapat berjalan ringan tanpa merender GUI 3D Gazebo)
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    saguling_field_server = Node(
        package='tyrant_gazebo_sim',
        executable='saguling_field_server',
        name='saguling_field_server',
        output='screen'
    )

    ea_dsra_node = Node(
        package='tyrant_gazebo_sim',
        executable='ea_dsra_node',
        name='ea_dsra_node',
        output='screen'
    )

    return LaunchDescription([
        saguling_field_server,
        ea_dsra_node
    ])
