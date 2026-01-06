from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    package_share_dir = get_package_share_directory('offline_media_publisher')
    config_file = os.path.join(package_share_dir, 'config', 'video_publisher.yaml')

    folder_path_arg = DeclareLaunchArgument(
        'folder_path',
        default_value='',
        description='Path to folder containing videos (required)'
    )

    fps_arg = DeclareLaunchArgument(
        'fps',
        default_value='50',
        description='Publishing rate in Hz (overrides native video FPS)'
    )

    return LaunchDescription([
        folder_path_arg,
        fps_arg,
        Node(
            package='offline_media_publisher',
            executable='video_publisher',
            name='video_publisher',
            output='screen',
            parameters=[
                config_file,
                {
                    'folder_path': LaunchConfiguration('folder_path'),
                    'fps': LaunchConfiguration('fps'),
                }
            ]
        )
    ])
