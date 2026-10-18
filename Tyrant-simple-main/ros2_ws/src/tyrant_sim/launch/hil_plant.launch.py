from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('tyrant_sim'),
        'config',
        'reduced_plant.yaml',
    )

    return LaunchDescription([
        Node(
            package='tyrant_sim',
            executable='tyrant_plant_sim',
            name='tyrant_plant_sim',
            output='screen',
            parameters=[config],
        ),
    ])
