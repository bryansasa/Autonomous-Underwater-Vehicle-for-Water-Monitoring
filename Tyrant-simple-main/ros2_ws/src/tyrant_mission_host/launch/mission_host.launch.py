from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackagePrefix


def generate_launch_description():
    default_plan = str(Path(get_package_share_directory('tyrant_mission_host'))/'config/two_depth_hil.yaml')
    arg = LaunchConfiguration
    # Launch the agent itself so shutdown signals reach it without a ros2-run wrapper.
    agent = PathJoinSubstitution([
        FindPackagePrefix('micro_ros_agent'), 'lib', 'micro_ros_agent', 'micro_ros_agent'])
    return LaunchDescription([
        DeclareLaunchArgument('plan', default_value=default_plan),
        DeclareLaunchArgument('payload_namespace', default_value='/tyrant/payload_sim'),
        DeclareLaunchArgument('teensy_simulated', default_value='true'),
        DeclareLaunchArgument('output_dir', default_value=str(Path.home()/'tyrant_missions')),
        DeclareLaunchArgument('start_agents', default_value='false'),
        DeclareLaunchArgument('teensy_port', default_value='/dev/tyrant-teensy'),
        DeclareLaunchArgument('esp_port', default_value='/dev/tyrant-esp'),
        DeclareLaunchArgument('publish_heartbeats', default_value='true'),
        ExecuteProcess(cmd=[agent,'serial',
                            '--dev',arg('teensy_port'),'-b','115200','-v4'],
                       condition=IfCondition(arg('start_agents')), output='screen'),
        ExecuteProcess(cmd=[agent,'serial',
                            '--dev',arg('esp_port'),'-b','115200','-v4'],
                       condition=IfCondition(arg('start_agents')), output='screen'),
        Node(package='tyrant_mission_host', executable='mission_host', output='screen', parameters=[{
            'plan': arg('plan'), 'payload_namespace': arg('payload_namespace'),
            'output_dir': arg('output_dir'),
            'teensy_simulated': ParameterValue(arg('teensy_simulated'), value_type=bool),
            'publish_heartbeats': ParameterValue(arg('publish_heartbeats'), value_type=bool),
        }]),
    ])
