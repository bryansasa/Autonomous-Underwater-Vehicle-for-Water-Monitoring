from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory('tyrant_teleop'))
    config = str(share / 'config' / 'ps_controller.yaml')

    return LaunchDescription([
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
            parameters=[{
                'deadzone': 0.03,
                'autorepeat_rate': 20.0,
            }],
        ),
        Node(
            package='tyrant_teleop',
            executable='tyrant_teleop',
            name='tyrant_teleop',
            output='screen',
            parameters=[config],
        ),
    ])
