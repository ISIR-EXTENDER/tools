from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('dynamic_parameters_identification'),
        'bringup',
        'config',
        'joint_sine_trajectory_params.yaml'
    ])

    return LaunchDescription([
        Node(
            package='dynamic_parameters_identification',
            executable='joints_sine_trajectory',
            name='joint_sine_trajectory',
            output='screen',
            parameters=[config_file],
        )
    ])
