from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    package_share_dir = get_package_share_directory('mediapipe_mocap')
    config_file = os.path.join(package_share_dir, 'config', 'hand_landmarks_node.yaml')
    
    return LaunchDescription([
        Node(
            package='mediapipe_mocap',
            executable='hand_landmarks_node',
            name='hand_landmarks_node',
            output='screen',
            parameters=[config_file]
        )
    ])
