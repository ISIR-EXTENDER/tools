from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('dynamic_parameters_identification'),
        'bringup',
        'config',
        'parameters_identification_params.yaml'
    ])

    return LaunchDescription([
        Node(
            package='dynamic_parameters_identification',
            executable='parameters_identification',
            name='parameters_identification',
            output='screen',
            parameters=[config_file],
        )
    ])
